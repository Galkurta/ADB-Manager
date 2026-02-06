"""
Wireless Connection Dialog - Connect to Android devices via WiFi

Provides UI for wireless ADB pairing and connection with multiple methods:
1. Manual Entry - Enter IP, Port, and Pairing Code manually
2. QR Scanner - Scan QR code from phone screenshot
3. QR Display - Generate QR code for phone to scan (mDNS-based)
"""

import logging
import re
import io
import asyncio
import secrets
import threading
import socket
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QCheckBox, QLabel,
    QMessageBox, QGroupBox, QTabWidget, QWidget,
    QFileDialog, QFrame
)
from PySide6.QtCore import Qt, Slot, QTimer, Signal
from PySide6.QtGui import QIntValidator, QPixmap, QImage, QClipboard

from utils.async_helper import safe_ensure_future

logger = logging.getLogger(__name__)


class WirelessDialog(QDialog):
    """Dialog for wireless ADB connection with multiple pairing methods"""
    
    def __init__(self, device_manager, parent=None):
        """
        Initialize Wireless Connection Dialog
        
        Args:
            device_manager: DeviceManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.device_manager = device_manager
        self._mdns_service = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup user interface"""
        self.setWindowTitle("Wireless Connection")
        self.setMinimumWidth(500)
        self.setMinimumHeight(450)
        
        layout = QVBoxLayout(self)
        
        # Tabs for different pairing methods
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_manual_tab(), "Manual Entry")
        self.tabs.addTab(self._create_qr_scan_tab(), "Scan QR Code")
        self.tabs.addTab(self._create_qr_display_tab(), "Display QR Code")
        layout.addWidget(self.tabs)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _create_manual_tab(self) -> QWidget:
        """Create manual entry tab with improved instructions"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Step-by-step instructions
        instructions = QLabel(
            "<b>Step-by-Step Wireless Pairing:</b><br><br>"
            "<b>1.</b> On your phone, go to <b>Settings → Developer Options</b><br>"
            "<b>2.</b> Enable <b>Wireless debugging</b><br>"
            "<b>3.</b> Tap <b>Pair device with pairing code</b><br>"
            "<b>4.</b> Enter the displayed information below<br>"
        )
        instructions.setWordWrap(True)
        instructions.setTextFormat(Qt.RichText)
        layout.addWidget(instructions)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Connection group
        conn_group = QGroupBox("Connection Details")
        conn_layout = QFormLayout(conn_group)
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        conn_layout.addRow("IP Address:", self.ip_input)
        
        self.port_input = QLineEdit("5555")
        self.port_input.setValidator(QIntValidator(1, 65535))
        conn_layout.addRow("Connection Port:", self.port_input)
        
        layout.addWidget(conn_group)
        
        # Pairing group
        self.pair_checkbox = QCheckBox("Pair Device First (Android 11+)")
        self.pair_checkbox.toggled.connect(self._toggle_pairing)
        layout.addWidget(self.pair_checkbox)
        
        self.pair_group = QGroupBox("Pairing Details")
        pair_layout = QFormLayout(self.pair_group)
        
        self.pair_code_input = QLineEdit()
        self.pair_code_input.setPlaceholderText("123456")
        self.pair_code_input.setMaxLength(6)
        pair_layout.addRow("Pairing Code:", self.pair_code_input)
        
        self.pair_port_input = QLineEdit()
        self.pair_port_input.setPlaceholderText("37171")
        self.pair_port_input.setValidator(QIntValidator(1, 65535))
        pair_layout.addRow("Pairing Port:", self.pair_port_input)
        
        self.pair_group.setVisible(False)
        layout.addWidget(self.pair_group)
        
        # Connect button
        self.manual_connect_btn = QPushButton("Connect")
        self.manual_connect_btn.setDefault(True)
        self.manual_connect_btn.clicked.connect(self._on_manual_connect)
        layout.addWidget(self.manual_connect_btn)
        
        layout.addStretch()
        return widget
    
    def _create_qr_scan_tab(self) -> QWidget:
        """Create QR code scanning tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        instructions = QLabel(
            "<b>Scan QR Code from Phone:</b><br><br>"
            "<b>1.</b> On your phone, go to <b>Wireless debugging</b><br>"
            "<b>2.</b> Tap <b>Pair device with QR code</b><br>"
            "<b>3.</b> Take a screenshot of the QR code<br>"
            "<b>4.</b> Load the screenshot here or paste from clipboard<br>"
        )
        instructions.setWordWrap(True)
        instructions.setTextFormat(Qt.RichText)
        layout.addWidget(instructions)
        
        # QR Preview
        self.qr_preview_label = QLabel("No QR code loaded")
        self.qr_preview_label.setAlignment(Qt.AlignCenter)
        self.qr_preview_label.setMinimumHeight(150)
        self.qr_preview_label.setStyleSheet("border: 1px solid gray; border-radius: 4px;")
        layout.addWidget(self.qr_preview_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        paste_btn = QPushButton("Paste from Clipboard")
        paste_btn.clicked.connect(self._paste_qr)
        btn_layout.addWidget(paste_btn)
        
        load_btn = QPushButton("Load Image...")
        load_btn.clicked.connect(self._load_qr_image)
        btn_layout.addWidget(load_btn)
        
        layout.addLayout(btn_layout)
        
        # Parsed info display
        self.qr_info_label = QLabel("")
        self.qr_info_label.setWordWrap(True)
        layout.addWidget(self.qr_info_label)
        
        # Connect button
        self.qr_connect_btn = QPushButton("Pair && Connect")
        self.qr_connect_btn.setEnabled(False)
        self.qr_connect_btn.clicked.connect(self._on_qr_connect)
        layout.addWidget(self.qr_connect_btn)
        
        layout.addStretch()
        
        # Store parsed QR data
        self._qr_data = None
        
        return widget
    
    def _create_qr_display_tab(self) -> QWidget:
        """Create QR code display tab for phone to scan"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        instructions = QLabel(
            "<b>Display QR Code for Phone to Scan:</b><br><br>"
            "<b>1.</b> Click <b>Generate QR Code</b> below<br>"
            "<b>2.</b> On your phone, go to <b>Wireless debugging</b><br>"
            "<b>3.</b> Tap <b>Pair device with QR code</b><br>"
            "<b>4.</b> Point the phone camera at the QR code below<br>"
        )
        instructions.setWordWrap(True)
        instructions.setTextFormat(Qt.RichText)
        layout.addWidget(instructions)
        
        # QR Display Container - separate placeholder text from QR image
        qr_container = QFrame()
        qr_container.setStyleSheet("border: 1px solid gray; border-radius: 4px;")
        qr_container.setMinimumHeight(280)
        qr_container_layout = QVBoxLayout(qr_container)
        qr_container_layout.setAlignment(Qt.AlignCenter)
        
        # Placeholder text (shown initially)
        self.qr_placeholder_label = QLabel("Click 'Generate QR Code' to create pairing code")
        self.qr_placeholder_label.setAlignment(Qt.AlignCenter)
        self.qr_placeholder_label.setStyleSheet("border: none;")
        qr_container_layout.addWidget(self.qr_placeholder_label)
        
        # QR image (hidden initially)
        self.qr_display_label = QLabel()
        self.qr_display_label.setAlignment(Qt.AlignCenter)
        self.qr_display_label.setStyleSheet("border: none;")
        self.qr_display_label.setVisible(False)
        qr_container_layout.addWidget(self.qr_display_label)
        
        layout.addWidget(qr_container)
        
        # Status/info
        self.mdns_status_label = QLabel("")
        self.mdns_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.mdns_status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.generate_qr_btn = QPushButton("Generate QR Code")
        self.generate_qr_btn.clicked.connect(self._generate_pairing_qr)
        btn_layout.addWidget(self.generate_qr_btn)
        
        self.stop_mdns_btn = QPushButton("Stop Service")
        self.stop_mdns_btn.setEnabled(False)
        self.stop_mdns_btn.clicked.connect(self._stop_mdns_service)
        btn_layout.addWidget(self.stop_mdns_btn)
        
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        return widget
    
    @Slot(bool)
    def _toggle_pairing(self, checked):
        """Toggle pairing group visibility"""
        self.pair_group.setVisible(checked)
        self.manual_connect_btn.setText("Pair && Connect" if checked else "Connect")
    
    @Slot()
    def _on_manual_connect(self):
        """Handle manual connect button click"""
        safe_ensure_future(self._manual_connect())
    
    def _validate_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        octets = ip.split('.')
        return all(0 <= int(octet) <= 255 for octet in octets)
    
    async def _manual_connect(self):
        """Perform manual wireless connection"""
        ip = self.ip_input.text().strip()
        port = self.port_input.text().strip()
        
        if not ip:
            QMessageBox.warning(self, "Invalid Input", "Please enter an IP address.")
            return
        
        if not self._validate_ip(ip):
            QMessageBox.warning(self, "Invalid IP", "Please enter a valid IP address.")
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
        
        # Handle pairing if enabled
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
            
            self.manual_connect_btn.setEnabled(False)
            self.manual_connect_btn.setText("Pairing...")
            
            try:
                success = await self.device_manager.pair_wireless(ip, pair_port_num, pair_code)
                if not success:
                    QMessageBox.critical(self, "Pairing Failed", "Failed to pair. Check the code and try again.")
                    self.manual_connect_btn.setEnabled(True)
                    self.manual_connect_btn.setText("Pair && Connect")
                    return
            except Exception as e:
                logger.error(f"Pairing error: {e}")
                QMessageBox.critical(self, "Pairing Error", f"Error during pairing: {str(e)}")
                self.manual_connect_btn.setEnabled(True)
                self.manual_connect_btn.setText("Pair && Connect")
                return
        
        # Connect
        self.manual_connect_btn.setText("Connecting...")
        self.manual_connect_btn.setEnabled(False)
        
        try:
            device = await self.device_manager.connect_wireless(ip, port_num)
            if device:
                QMessageBox.information(self, "Success", f"Connected to {device.serial}")
                self.accept()
            else:
                QMessageBox.critical(self, "Connection Failed", "Failed to connect. Ensure wireless debugging is enabled.")
                self.manual_connect_btn.setEnabled(True)
                self.manual_connect_btn.setText("Connect")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            QMessageBox.critical(self, "Connection Error", f"Error: {str(e)}")
            self.manual_connect_btn.setEnabled(True)
            self.manual_connect_btn.setText("Connect")
    
    @Slot()
    def _paste_qr(self):
        """Paste QR image from clipboard"""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        
        if image.isNull():
            QMessageBox.warning(self, "No Image", "No image found in clipboard.")
            return
        
        self._process_qr_image(image)
    
    @Slot()
    def _load_qr_image(self):
        """Load QR image from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select QR Code Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            image = QImage(file_path)
            if image.isNull():
                QMessageBox.warning(self, "Invalid Image", "Could not load the image.")
                return
            self._process_qr_image(image)
    
    def _process_qr_image(self, image: QImage):
        """Process QR code image and extract pairing info"""
        try:
            from pyzbar.pyzbar import decode
            from PIL import Image
            
            # Convert QImage to PIL Image
            buffer = image.bits().tobytes()
            pil_image = Image.frombytes(
                'RGBA' if image.hasAlphaChannel() else 'RGB',
                (image.width(), image.height()),
                buffer
            )
            
            # Decode QR codes
            decoded = decode(pil_image)
            
            if not decoded:
                self.qr_preview_label.setText("No QR code detected in image")
                self.qr_info_label.setText("")
                self.qr_connect_btn.setEnabled(False)
                return
            
            # Get QR data
            qr_text = decoded[0].data.decode('utf-8')
            logger.info(f"QR code decoded: {qr_text}")
            
            # Parse ADB pairing data
            # Format: WIFI:T:ADB;S:<service>;P:<password>;; or similar
            parsed = self._parse_qr_data(qr_text)
            
            if parsed:
                # Show preview
                pixmap = QPixmap.fromImage(image).scaled(150, 150, Qt.KeepAspectRatio)
                self.qr_preview_label.setPixmap(pixmap)
                
                ip, port, code = parsed
                self.qr_info_label.setText(f"<b>Detected:</b><br>IP: {ip}<br>Port: {port}<br>Code: {code}")
                self.qr_connect_btn.setEnabled(True)
                self._qr_data = parsed
            else:
                self.qr_preview_label.setText("QR code found but format not recognized")
                self.qr_info_label.setText(f"Raw data: {qr_text[:100]}...")
                self.qr_connect_btn.setEnabled(False)
                
        except ImportError:
            QMessageBox.warning(self, "Missing Library", "pyzbar library not installed properly.")
        except Exception as e:
            logger.error(f"QR processing error: {e}")
            self.qr_preview_label.setText(f"Error processing image: {str(e)}")
            self.qr_connect_btn.setEnabled(False)
    
    def _parse_qr_data(self, qr_text: str) -> Optional[Tuple[str, int, str]]:
        """
        Parse QR code data for ADB pairing info
        
        Returns:
            Tuple of (ip, port, pairing_code) or None
        """
        # Try WIFI:T:ADB format
        if qr_text.startswith("WIFI:"):
            parts = {}
            for segment in qr_text.replace("WIFI:", "").rstrip(";").split(";"):
                if ":" in segment:
                    key, value = segment.split(":", 1)
                    parts[key] = value
            
            if "S" in parts and "P" in parts:
                # Service name might contain IP:PORT
                service = parts.get("S", "")
                password = parts.get("P", "")
                
                # Try to extract IP from service or other fields
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+):(\d+)', service)
                if ip_match:
                    return (ip_match.group(1), int(ip_match.group(2)), password)
        
        # Try plain IP:PORT:CODE format
        match = re.match(r'^(\d+\.\d+\.\d+\.\d+):(\d+):(\d{6})$', qr_text)
        if match:
            return (match.group(1), int(match.group(2)), match.group(3))
        
        return None
    
    @Slot()
    def _on_qr_connect(self):
        """Handle QR connect button click"""
        if self._qr_data:
            safe_ensure_future(self._qr_pair_and_connect())
    
    async def _qr_pair_and_connect(self):
        """Pair and connect using QR data"""
        if not self._qr_data:
            return
        
        ip, port, code = self._qr_data
        
        self.qr_connect_btn.setEnabled(False)
        self.qr_connect_btn.setText("Pairing...")
        
        try:
            # First pair
            success = await self.device_manager.pair_wireless(ip, port, code)
            if not success:
                QMessageBox.critical(self, "Pairing Failed", "Failed to pair with device.")
                self.qr_connect_btn.setEnabled(True)
                self.qr_connect_btn.setText("Pair && Connect")
                return
            
            # Then connect (port might be different for connection vs pairing)
            self.qr_connect_btn.setText("Connecting...")
            
            # Try common connection ports
            connection_port = 5555  # Default ADB port
            device = await self.device_manager.connect_wireless(ip, connection_port)
            
            if device:
                QMessageBox.information(self, "Success", f"Connected to {device.serial}")
                self.accept()
            else:
                QMessageBox.warning(
                    self, "Partial Success",
                    "Pairing successful but connection failed.\n\n"
                    "Try using Manual Entry tab with the device's wireless debugging port."
                )
                self.qr_connect_btn.setEnabled(True)
                self.qr_connect_btn.setText("Pair && Connect")
                
        except Exception as e:
            logger.error(f"QR connect error: {e}")
            QMessageBox.critical(self, "Error", str(e))
            self.qr_connect_btn.setEnabled(True)
            self.qr_connect_btn.setText("Pair && Connect")
    
    @Slot()
    def _generate_pairing_qr(self):
        """Generate QR code for phone to scan (mDNS-based)"""
        try:
            import qrcode
            from zeroconf import Zeroconf, ServiceInfo
            
            # Get local IP
            local_ip = self._get_local_ip()
            if not local_ip:
                QMessageBox.warning(self, "Network Error", "Could not determine local IP address.")
                return
            
            # Generate random service name and password
            service_name = f"adb-{secrets.token_hex(4)}"
            password = f"{secrets.randbelow(900000) + 100000}"  # 6-digit code
            port = 5555 + secrets.randbelow(100)  # Random port
            
            # Create QR code data
            # Format: WIFI:T:ADB;S:<service_name>;P:<password>;;
            qr_data = f"WIFI:T:ADB;S:{service_name}@{local_ip}:{port};P:{password};;"
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(qr_data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="white", back_color="#2b2b2b")
            
            # Create composite image with QR + text below (dark theme)
            from PIL import Image, ImageDraw, ImageFont
            
            qr_size = qr_img.size[0]
            text_lines = [
                f"IP: {local_ip}",
                f"Port: {port}",
                f"Code: {password}"
            ]
            
            # Calculate text height (approximately 20px per line + padding)
            line_height = 22
            text_padding = 15
            text_height = len(text_lines) * line_height + text_padding * 2
            
            # Create larger canvas
            canvas_width = qr_size
            canvas_height = qr_size + text_height
            canvas = Image.new('RGB', (canvas_width, canvas_height), color='#2b2b2b')
            
            # Paste QR code at top (convert to RGB first)
            qr_rgb = qr_img.convert('RGB')
            canvas.paste(qr_rgb, (0, 0, qr_size, qr_size))
            
            # Draw text below QR
            draw = ImageDraw.Draw(canvas)
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            y = qr_size + text_padding
            for line in text_lines:
                # Get text width for centering
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (canvas_width - text_width) // 2
                draw.text((x, y), line, fill='white', font=font)
                y += line_height
            
            # Convert to QPixmap
            buffer = io.BytesIO()
            canvas.save(buffer, format='PNG')
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.read())
            
            # Scale to fit container while maintaining aspect ratio
            pixmap = pixmap.scaled(250, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Hide placeholder, show QR image
            self.qr_placeholder_label.setVisible(False)
            self.qr_display_label.setVisible(True)
            self.qr_display_label.setPixmap(pixmap)
            
            # Start mDNS service in background thread (avoids UI freeze)
            self._mdns_thread = threading.Thread(
                target=self._start_mdns_service,
                args=(service_name, local_ip, port, password),
                daemon=True
            )
            self._mdns_thread.start()
            
            # Clear status label (info is now in image)
            self.mdns_status_label.setText("")
            
            self.generate_qr_btn.setEnabled(False)
            self.stop_mdns_btn.setEnabled(True)
            
        except ImportError as e:
            QMessageBox.warning(self, "Missing Library", f"Required library not installed: {e}")
        except Exception as e:
            logger.error(f"QR generation error: {e}")
            QMessageBox.warning(self, "Error", f"Failed to generate QR code: {e}")
    
    def _get_local_ip(self) -> Optional[str]:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None
    
    def _start_mdns_service(self, name: str, ip: str, port: int, password: str):
        """Start mDNS service for pairing"""
        try:
            from zeroconf import Zeroconf, ServiceInfo
            import socket
            
            self._zeroconf = Zeroconf()
            
            # Create service info for ADB pairing
            service_type = "_adb-tls-pairing._tcp.local."
            service_name = f"{name}.{service_type}"
            
            info = ServiceInfo(
                service_type,
                service_name,
                addresses=[socket.inet_aton(ip)],
                port=port,
                properties={
                    "pw": password,
                },
            )
            
            self._zeroconf.register_service(info)
            self._mdns_service = info
            
            logger.info(f"mDNS service registered: {service_name}")
            
        except Exception as e:
            logger.error(f"mDNS service error: {e}")
            self.mdns_status_label.setText(f"mDNS Error: {e}")
    
    @Slot()
    def _stop_mdns_service(self):
        """Stop mDNS service"""
        try:
            if self._mdns_service and hasattr(self, '_zeroconf'):
                self._zeroconf.unregister_service(self._mdns_service)
                self._zeroconf.close()
                self._mdns_service = None
                logger.info("mDNS service stopped")
        except Exception as e:
            logger.error(f"Error stopping mDNS: {e}")
        
        # Show placeholder, hide QR image
        self.qr_display_label.setVisible(False)
        self.qr_display_label.clear()
        self.qr_placeholder_label.setVisible(True)
        self.mdns_status_label.setText("")
        self.generate_qr_btn.setEnabled(True)
        self.stop_mdns_btn.setEnabled(False)
    
    def closeEvent(self, event):
        """Clean up on close"""
        self._stop_mdns_service()
        super().closeEvent(event)
