"""
Device Info Widget - Display detailed device information

This widget shows comprehensive information about the connected device.
"""

import asyncio
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QPushButton,
    QGroupBox, QScrollArea
)
from PySide6.QtCore import Qt, Slot

from utils.adb_wrapper import ADBWrapper

logger = logging.getLogger(__name__)


class DeviceInfoWidget(QWidget):
    """Device information widget"""
    
    def __init__(self, adb: ADBWrapper):
        """
        Initialize Device Info Widget
        
        Args:
            adb: ADB wrapper instance
        """
        super().__init__()
        self.adb = adb
        self.current_device = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        device_group = QGroupBox("Device Information")
        device_layout = QFormLayout()
        
        self.model_label = QLabel("N/A")
        self.manufacturer_label = QLabel("N/A")
        self.serial_label = QLabel("N/A")
        self.android_version_label = QLabel("N/A")
        self.sdk_version_label = QLabel("N/A")
        self.kernel_label = QLabel("N/A")
        self.rom_label = QLabel("N/A")
        
        device_layout.addRow("Model:", self.model_label)
        device_layout.addRow("Manufacturer:", self.manufacturer_label)
        device_layout.addRow("Serial:", self.serial_label)
        device_layout.addRow("Android Version:", self.android_version_label)
        device_layout.addRow("SDK Version:", self.sdk_version_label)
        device_layout.addRow("Kernel:", self.kernel_label)
        device_layout.addRow("ROM:", self.rom_label)
        
        device_group.setLayout(device_layout)
        scroll_layout.addWidget(device_group)
        
        hardware_group = QGroupBox("Hardware Information")
        hardware_layout = QFormLayout()
        
        self.cpu_label = QLabel("N/A")
        self.chipset_label = QLabel("N/A")
        self.ram_label = QLabel("N/A")
        self.screen_label = QLabel("N/A")
        self.battery_label = QLabel("N/A")
        
        hardware_layout.addRow("CPU:", self.cpu_label)
        hardware_layout.addRow("Chipset:", self.chipset_label)
        hardware_layout.addRow("RAM:", self.ram_label)
        hardware_layout.addRow("Screen:", self.screen_label)
        hardware_layout.addRow("Battery:", self.battery_label)
        
        hardware_group.setLayout(hardware_layout)
        scroll_layout.addWidget(hardware_group)
        
        storage_group = QGroupBox("Storage Information")
        storage_layout = QFormLayout()
        
        self.internal_storage_label = QLabel("N/A")
        self.external_storage_label = QLabel("N/A")
        
        storage_layout.addRow("Internal Storage:", self.internal_storage_label)
        storage_layout.addRow("External Storage:", self.external_storage_label)
        
        storage_group.setLayout(storage_layout)
        scroll_layout.addWidget(storage_group)
        
        network_group = QGroupBox("Network Information")
        network_layout = QFormLayout()
        
        self.wifi_ip_label = QLabel("N/A")
        self.mac_address_label = QLabel("N/A")
        
        network_layout.addRow("WiFi IP:", self.wifi_ip_label)
        network_layout.addRow("MAC Address:", self.mac_address_label)
        
        network_group.setLayout(network_layout)
        scroll_layout.addWidget(network_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        self.refresh_btn = QPushButton("Refresh Info")
        self.refresh_btn.clicked.connect(self._refresh_info)
        layout.addWidget(self.refresh_btn)
    
    def set_device(self, device: str):
        """
        Set current device and load info
        
        Args:
            device: Device serial number
        """
        self.current_device = device
        self.serial_label.setText(device)
        asyncio.ensure_future(self._load_device_info())
    
    async def _load_device_info(self):
        """Load device information"""
        if not self.current_device:
            return
        
        try:
            model = await self._get_prop("ro.product.model")
            manufacturer = await self._get_prop("ro.product.manufacturer")
            android_version = await self._get_prop("ro.build.version.release")
            sdk_version = await self._get_prop("ro.build.version.sdk")
            
            self.model_label.setText(model)
            self.manufacturer_label.setText(manufacturer)
            self.android_version_label.setText(android_version)
            self.sdk_version_label.setText(f"API {sdk_version}")
            
            kernel = await self._get_prop("ro.build.version.release")
            kernel_full = await self.adb.shell("uname -r", self.current_device)
            if kernel_full.strip():
                self.kernel_label.setText(kernel_full.strip())
            
            rom_name = await self._get_prop("ro.build.display.id")
            if rom_name and rom_name != "N/A":
                self.rom_label.setText(rom_name)
            else:
                rom_name = await self._get_prop("ro.build.version.incremental")
                self.rom_label.setText(rom_name)
            
            cpu_info = await self.adb.shell("getprop ro.product.cpu.abi", self.current_device)
            self.cpu_label.setText(cpu_info.strip())
            
            chipset = await self._get_prop("ro.board.platform")
            if chipset == "N/A" or not chipset:
                chipset = await self._get_prop("ro.hardware")
            if chipset == "N/A" or not chipset:
                chipset = await self._get_prop("ro.product.board")
            self.chipset_label.setText(chipset if chipset and chipset != "N/A" else "Unknown")
            
            meminfo = await self.adb.shell("cat /proc/meminfo | grep MemTotal", self.current_device)
            if meminfo:
                ram_kb = meminfo.split()[1]
                ram_gb = int(ram_kb) // 1024 // 1024
                self.ram_label.setText(f"{ram_gb} GB")
            
            screen_size = await self.adb.shell("wm size", self.current_device)
            if "Physical size:" in screen_size:
                resolution = screen_size.split("Physical size:")[1].strip()
                self.screen_label.setText(resolution)
            
            battery_output = await self.adb.shell("dumpsys battery", self.current_device)
            
            level = None
            status_num = None
            
            for line in battery_output.split('\n'):
                line = line.strip()
                if line.startswith('level:'):
                    level = line.split(':')[1].strip()
                elif line.startswith('status:'):
                    status_num = line.split(':')[1].strip()
            
            if level:
                status_map = {"1": "Unknown", "2": "Charging", "3": "Discharging", "4": "Not charging", "5": "Full"}
                status_text = status_map.get(status_num, "")
                
                battery_display = f"{level}%"
                if status_text:
                    battery_display += f" ({status_text})"
                    
                self.battery_label.setText(battery_display)
            
            storage = await self.adb.shell("df /data | tail -1", self.current_device)
            if storage:
                parts = storage.split()
                if len(parts) >= 4:
                    total = int(parts[1]) // 1024 // 1024  # Convert to GB
                    used = int(parts[2]) // 1024 // 1024
                    self.internal_storage_label.setText(f"{used} GB / {total} GB")
            
            wifi_ip = await self.adb.shell("ip addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1", self.current_device)
            if wifi_ip.strip():
                self.wifi_ip_label.setText(wifi_ip.strip())
            else:
                self.wifi_ip_label.setText("Not connected")
            
            mac = await self.adb.shell("cat /sys/class/net/wlan0/address 2>/dev/null", self.current_device)
            if not mac.strip():
                mac = await self.adb.shell("ip link show wlan0 2>/dev/null | grep 'link/ether' | awk '{print $2}'", self.current_device)
            if not mac.strip():
                mac = await self.adb.shell("settings get secure bluetooth_address 2>/dev/null", self.current_device)
            
            if mac.strip() and mac.strip() != "null":
                self.mac_address_label.setText(mac.strip().upper())
            else:
                self.mac_address_label.setText("Unavailable")
            
            logger.info("Device info loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load device info: {e}")
    
    async def _get_prop(self, prop: str) -> str:
        """
        Get device property
        
        Args:
            prop: Property name
        
        Returns:
            Property value
        """
        try:
            output = await self.adb.shell(f"getprop {prop}", self.current_device)
            return output.strip()
        except Exception:
            return "N/A"
    
    @Slot()
    def _refresh_info(self):
        """Refresh device information"""
        asyncio.ensure_future(self._load_device_info())
