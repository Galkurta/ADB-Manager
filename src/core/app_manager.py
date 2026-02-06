"""Application Manager - APK installation and app management"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal

from utils.adb_wrapper import ADBWrapper

logger = logging.getLogger(__name__)


@dataclass
class Package:
    """Represents an installed application package"""
    package_name: str
    label: str = ""
    version: str = ""
    is_system: bool = False
    is_enabled: bool = True
    install_location: str = ""
    
    @property
    def display_name(self) -> str:
        """Get user-friendly display name"""
        return self.label if self.label else self.package_name


class AppManager(QObject):
    """Manages application operations on Android devices"""
    
    install_progress = Signal(int, str)
    install_complete = Signal(bool, str)
    
    def __init__(self, adb: ADBWrapper):
        super().__init__()
        self.adb = adb
        logger.info("App Manager initialized")
    
    async def list_packages(
        self,
        device: str,
        filter_type: str = 'all'
    ) -> List[Package]:
        """List installed packages (filter: all/user/system/enabled/disabled)"""
        try:
            cmd = "pm list packages"
            
            if filter_type == 'user':
                cmd += " -3"
            elif filter_type == 'system':
                cmd += " -s"
            elif filter_type == 'enabled':
                cmd += " -e"
            elif filter_type == 'disabled':
                cmd += " -d"
            
            output = await self.adb.shell(cmd, device)
            
            packages = []
            for line in output.strip().split('\n'):
                if not line.startswith('package:'):
                    continue
                package_name = line.replace('package:', '').strip()
                
                is_system = filter_type == 'system'
                is_enabled = filter_type != 'disabled'
                label = self._derive_label_from_package(package_name)
                
                packages.append(Package(
                    package_name=package_name,
                    label=label,
                    is_system=is_system,
                    is_enabled=is_enabled
                ))
            
            packages.sort(key=lambda p: p.display_name.lower())
            
            logger.info(f"Found {len(packages)} packages (filter: {filter_type})")
            return packages
            
        except Exception as e:
            logger.error(f"Failed to list packages: {e}")
            return []
    
    def _derive_label_from_package(self, package_name: str) -> str:
        """Derive human-readable label from package name"""
        parts = package_name.split('.')
        if not parts:
            return package_name
        
        name = parts[-1]
        
        if name in ('app', 'android', 'google', 'core', 'service', 'services'):
            if len(parts) >= 2:
                name = parts[-2]
        result = ""
        for char in name:
            if char.isupper() and result:
                result += " "
            result += char
        
        return result.capitalize() if result else package_name
    
    async def install_apk(
        self,
        device: str,
        apk_path: Path,
        options: Optional[List[str]] = None
    ) -> bool:
        """Install APK on device"""
        try:
            logger.info(f"Installing {apk_path.name}")
            self.install_progress.emit(0, apk_path.name)
            success = await self.adb.install_apk(apk_path, device, options)
            
            self.install_complete.emit(success, apk_path.name)
            
            if success:
                logger.info(f"Successfully installed {apk_path.name}")
            else:
                logger.error(f"Failed to install {apk_path.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"APK installation failed: {e}")
            self.install_complete.emit(False, apk_path.name)
            return False
    
    async def uninstall_package(self, device: str, package: str) -> bool:
        """Uninstall package from device"""
        try:
            logger.info(f"Uninstalling {package}")
            success = await self.adb.uninstall_package(package, device)
            
            if success:
                logger.info(f"Successfully uninstalled {package}")
            else:
                logger.error(f"Failed to uninstall {package}")
            
            return success
            
        except Exception as e:
            logger.error(f"Package uninstallation failed: {e}")
            return False
    
    async def disable_package(self, device: str, package: str) -> bool:
        """Disable package"""
        try:
            await self.adb.shell(f"pm disable-user {package}", device)
            logger.info(f"Disabled {package}")
            return True
        except Exception as e:
            logger.error(f"Failed to disable {package}: {e}")
            return False
    
    async def enable_package(self, device: str, package: str) -> bool:
        """Enable package"""
        try:
            await self.adb.shell(f"pm enable {package}", device)
            logger.info(f"Enabled {package}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable {package}: {e}")
            return False
    
    async def clear_app_data(self, device: str, package: str) -> bool:
        """Clear application data"""
        try:
            await self.adb.shell(f"pm clear {package}", device)
            logger.info(f"Cleared data for {package}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear data for {package}: {e}")
            return False
    
    async def clear_app_cache(self, device: str, package: str) -> bool:
        """Clear application cache"""
        try:
            output = await self.adb.shell(f"pm path {package}", device)
            if not output:
                return False
            
            await self.adb.shell(f"rm -rf /data/data/{package}/cache/*", device)
            logger.info(f"Cleared cache for {package}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache for {package}: {e}")
            return False
    
    async def launch_app(self, device: str, package: str) -> bool:
        """Launch application"""
        try:
            output = await self.adb.shell(
                f"cmd package resolve-activity --brief {package} | tail -n 1",
                device
            )
            
            if not output or '/' not in output:
                logger.error(f"Could not find main activity for {package}")
                return False
            
            activity = output.strip()
            await self.adb.shell(f"am start -n {activity}", device)
            logger.info(f"Launched {package}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to launch {package}: {e}")
            return False
