"""
Device Manager - Device detection, connection, and monitoring

This module handles device discovery, wireless connections, and real-time
device state monitoring using Qt signals.
"""

import asyncio
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal, QTimer

from utils.adb_wrapper import ADBWrapper, DeviceUnauthorizedError
from utils.async_helper import is_async_busy, safe_ensure_future

logger = logging.getLogger(__name__)


@dataclass
class Device:
    """Represents an Android device"""
    serial: str
    state: str  # 'device', 'offline', 'unauthorized'
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    android_version: Optional[str] = None
    sdk_version: Optional[str] = None
    cpu_abi: Optional[str] = None
    
    @property
    def is_authorized(self) -> bool:
        """Check if device is authorized for debugging"""
        return self.state == "device"
    
    @property
    def display_name(self) -> str:
        """Get user-friendly display name"""
        if self.model and self.manufacturer:
            return f"{self.manufacturer} {self.model}"
        elif self.model:
            return self.model
        
        # Clean up mDNS-style serials like "adb-XXXXX-YYYYY._adb-tls-connect._tcp."
        serial = self.serial
        if '._adb-tls-' in serial:
            # Extract just the identifier part before the mDNS suffix
            serial = serial.split('._adb-')[0]
        
        return serial
    
    def __str__(self) -> str:
        return f"{self.display_name} ({self.serial})"


class DeviceManager(QObject):
    """
    Manages Android device connections and monitoring
    
    Signals:
        device_connected: Emitted when a new device is connected
        device_disconnected: Emitted when a device is disconnected
        device_unauthorized: Emitted when a device is unauthorized
        devices_updated: Emitted when device list changes
    """
    
    device_connected = Signal(Device)
    device_disconnected = Signal(str)  # serial
    device_unauthorized = Signal(str)  # serial
    devices_updated = Signal(list)  # List[Device]
    
    def __init__(self, adb: ADBWrapper):
        """
        Initialize Device Manager
        
        Args:
            adb: ADB wrapper instance
        """
        super().__init__()
        self.adb = adb
        self._devices: Dict[str, Device] = {}
        self._monitor_timer: Optional[QTimer] = None
        self._monitoring = False
        self._check_in_progress = False  # Prevent concurrent checks
        logger.info("Device Manager initialized")
    
    async def scan_devices(self) -> List[Device]:
        """
        Scan for connected devices
        
        Returns:
            List of Device objects
        """
        try:
            device_list = await self.adb.get_devices()
            devices = []
            
            for dev_info in device_list:
                serial = dev_info['serial']
                state = dev_info['state']
                
                device = Device(
                    serial=serial,
                    state=state,
                    model=dev_info.get('model'),
                )
                
                if state == "device":
                    try:
                        props = await self.adb.get_device_info(serial)
                        device.model = props.get('ro.product.model', device.model)
                        device.manufacturer = props.get('ro.product.manufacturer')
                        device.android_version = props.get('ro.build.version.release')
                        device.sdk_version = props.get('ro.build.version.sdk')
                        device.cpu_abi = props.get('ro.product.cpu.abi')
                    except Exception as e:
                        logger.warning(f"Failed to get device info for {serial}: {e}")
                
                devices.append(device)
                logger.info(f"Found device: {device}")
            
            return devices
            
        except Exception as e:
            logger.error(f"Device scan failed: {e}")
            return []
    
    async def pair_wireless(self, ip: str, port: int, code: str) -> bool:
        """
        Pair with a device for wireless debugging (Android 11+)
        
        Args:
            ip: Device IP address
            port: Pairing port (from Wireless Debugging settings)
            code: 6-digit pairing code
        
        Returns:
            True if pairing successful
        """
        logger.info(f"Attempting wireless pairing with {ip}:{port}")
        success = await self.adb.pair_wireless(ip, port, code)
        if success:
            logger.info("Wireless pairing successful")
        else:
            logger.error("Wireless pairing failed")
        return success
    
    async def connect_wireless(self, ip: str, port: int = 5555) -> Optional[Device]:
        """
        Connect to a device wirelessly
        
        Args:
            ip: Device IP address
            port: ADB port (default: 5555)
        
        Returns:
            Device object if successful, None otherwise
        """
        logger.info(f"Attempting wireless connection to {ip}:{port}")
        
        success = await self.adb.connect_wireless(ip, port)
        if not success:
            logger.error("Wireless connection failed")
            return None
        
        devices = await self.scan_devices()
        for device in devices:
            if ip in device.serial:
                logger.info(f"Wireless connection successful: {device}")
                return device
        
        return None
    
    async def disconnect_wireless(self, ip: str, port: int = 5555) -> bool:
        """
        Disconnect from a wireless device
        
        Args:
            ip: Device IP address
            port: ADB port (default: 5555)
        
        Returns:
            True if successful
        """
        return await self.adb.disconnect_wireless(ip, port)
    
    async def get_device_info(self, serial: str) -> Optional[Device]:
        """
        Get detailed information about a specific device
        
        Args:
            serial: Device serial number
        
        Returns:
            Device object or None if not found
        """
        devices = await self.scan_devices()
        for device in devices:
            if device.serial == serial:
                return device
        return None
    
    def start_monitoring(self, interval_ms: int = 2000):
        """
        Start monitoring for device changes
        
        Args:
            interval_ms: Polling interval in milliseconds
        """
        if self._monitoring:
            logger.warning("Device monitoring already started")
            return
        
        self._monitoring = True
        self._monitor_interval = interval_ms
        logger.info(f"Device monitoring started (interval: {interval_ms}ms)")
        
        # Initial scan after a short delay to ensure event loop is running
        QTimer.singleShot(100, self._on_timer_tick)
    
    def _on_timer_tick(self):
        """Handle timer tick - schedule async device check"""
        if not self._monitoring:
            return
        
        # Skip if a check is already in progress or if another async op is busy
        if self._check_in_progress or is_async_busy():
            QTimer.singleShot(500, self._on_timer_tick)
            return
        
        task = safe_ensure_future(self._check_devices_and_reschedule())
        if task is None:
            QTimer.singleShot(500, self._on_timer_tick)
    
    async def _check_devices_and_reschedule(self):
        """Check devices then reschedule the next check"""
        try:
            await self._check_devices()
        finally:
            if self._monitoring:
                QTimer.singleShot(self._monitor_interval, self._on_timer_tick)
    
    def stop_monitoring(self):
        """Stop monitoring for device changes"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        logger.info("Device monitoring stopped")
    
    async def _check_devices(self):
        """Check for device changes and emit signals"""
        if self._check_in_progress:
            return
        
        self._check_in_progress = True
        try:
            current_devices = await self.scan_devices()
            current_serials = {dev.serial for dev in current_devices}
            previous_serials = set(self._devices.keys())
            
            devices_changed = False
            
            for device in current_devices:
                if device.serial not in previous_serials:
                    logger.info(f"New device detected: {device}")
                    self.device_connected.emit(device)
                    devices_changed = True
                    
                    if not device.is_authorized:
                        self.device_unauthorized.emit(device.serial)
                
                self._devices[device.serial] = device
            
            for serial in previous_serials - current_serials:
                logger.info(f"Device disconnected: {serial}")
                self.device_disconnected.emit(serial)
                del self._devices[serial]
                devices_changed = True
            
            # Only emit updated list if devices actually changed
            if devices_changed:
                logger.debug(f"DeviceManager: Emitting devices_updated with {len(self._devices)} devices")
                self.devices_updated.emit(list(self._devices.values()))
            
        except RuntimeError as e:
            if "Cannot enter into task" not in str(e):
                logger.error(f"Device check runtime error: {e}")
        except Exception as e:
            logger.error(f"Device check failed: {e}")
        finally:
            self._check_in_progress = False
    
    def get_connected_devices(self) -> List[Device]:
        """
        Get currently connected devices from cache
        
        Returns:
            List of cached Device objects
        """
        return list(self._devices.values())
    
    def get_device(self, serial: str) -> Optional[Device]:
        """
        Get a specific device from cache
        
        Args:
            serial: Device serial number
        
        Returns:
            Device object or None
        """
        return self._devices.get(serial)
