"""
ADB Wrapper - Asynchronous interface for Android Debug Bridge commands

This module provides a clean, async interface for executing ADB commands
with proper error handling and timeout management.
"""

import asyncio
import logging
import platform
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Callable
import re

logger = logging.getLogger(__name__)


class ADBError(Exception):
    """Base exception for ADB-related errors"""
    pass


class DeviceNotFoundError(ADBError):
    """Raised when no device is found or device is offline"""
    pass


class DeviceUnauthorizedError(ADBError):
    """Raised when device is not authorized for debugging"""
    pass


class MultipleDevicesError(ADBError):
    """Raised when multiple devices are connected but no specific device is selected"""
    pass


class ADBWrapper:
    """
    Asynchronous wrapper for ADB commands
    
    Handles command execution, output parsing, and error management.
    """
    
    def __init__(self, adb_path: Optional[Path] = None):
        """
        Initialize ADB wrapper
        
        Args:
            adb_path: Path to ADB binary. If None, uses system ADB.
        """
        self.adb_path = adb_path or self._find_adb()
        self._server_started = False
        logger.info(f"ADB wrapper initialized with binary: {self.adb_path}")
    
    def _find_adb(self) -> Path:
        """
        Find ADB binary in system PATH or bundled binaries
        
        Returns:
            Path to ADB executable
        """
        system = platform.system().lower()
        base_path = Path(__file__).parent.parent.parent / "binaries" / "adb"
        
        # Check specific platform folder first (user structure)
        if system == "windows":
            platform_path = base_path / "windows" / "adb.exe"
            if platform_path.exists():
                return platform_path
        elif system == "darwin":
            platform_path = base_path / "macos" / "adb"
            if platform_path.exists():
                return platform_path
        else:  # Linux
            platform_path = base_path / "linux" / "adb"
            if platform_path.exists():
                return platform_path
        
        # Check root of adb folder (CI structure)
        adb_exe = base_path / ("adb.exe" if system == "windows" else "adb")
        if adb_exe.exists():
            return adb_exe
        
        return Path("adb")
    
    async def execute(
        self,
        args: List[str],
        timeout: int = 30,
        device: Optional[str] = None,
        skip_server_check: bool = False
    ) -> Tuple[str, str, int]:
        """
        Execute an ADB command asynchronously
        
        Args:
            args: Command arguments (without 'adb' prefix)
            timeout: Command timeout in seconds
            device: Device serial number (optional)
            skip_server_check: Skip ADB server startup check (internal use)
        
        Returns:
            Tuple of (stdout, stderr, return_code)
        
        Raises:
            ADBError: If command execution fails
            asyncio.TimeoutError: If command times out
        """
        if not self._server_started and not skip_server_check:
            await self._start_server()
        cmd = [str(self.adb_path)]
        if device:
            cmd.extend(["-s", device])
        cmd.extend(args)
        
        logger.debug(f"Executing ADB command: {' '.join(cmd)}")
        
        try:
            import sys
            if sys.platform == 'win32':
                import subprocess
                creationflags = subprocess.CREATE_NO_WINDOW
            else:
                creationflags = 0
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=creationflags
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            
            logger.debug(f"Command output: {stdout_str[:200]}")
            
            if not skip_server_check:
                self._check_errors(stderr_str)
            
            return stdout_str, stderr_str, process.returncode
            
        except asyncio.TimeoutError:
            logger.error(f"ADB command timed out after {timeout}s")
            raise
        except Exception as e:
            logger.error(f"ADB command failed: {e}")
            raise ADBError(f"Command execution failed: {e}")
    
    def _check_errors(self, stderr: str):
        """
        Check stderr for common ADB errors and raise appropriate exceptions
        
        Args:
            stderr: Standard error output from ADB command
        
        Raises:
            DeviceNotFoundError: If no device is found
            DeviceUnauthorizedError: If device is unauthorized
            MultipleDevicesError: If multiple devices are connected
        """
        stderr_lower = stderr.lower()
        
        if "no devices" in stderr_lower or "device not found" in stderr_lower:
            raise DeviceNotFoundError("No Android devices found")
        
        if "unauthorized" in stderr_lower:
            raise DeviceUnauthorizedError(
                "Device is not authorized. Please check the confirmation dialog on your device."
            )
        
        if "more than one device" in stderr_lower:
            raise MultipleDevicesError(
                "Multiple devices connected. Please specify a device serial number."
            )
    
    async def _start_server(self):
        """Start ADB server if not already running"""
        try:
            await self.execute(["start-server"], timeout=10, skip_server_check=True)
            self._server_started = True
            logger.info("ADB server started successfully")
        except Exception as e:
            logger.warning(f"Failed to start ADB server: {e}")
    
    async def restart_server(self) -> bool:
        """
        Restart ADB server (kill and start)
        
        Useful for fixing authorization issues and stale connections.
        
        Returns:
            True if restart successful
        """
        try:
            # Kill server
            logger.info("Killing ADB server...")
            await self.execute(["kill-server"], timeout=10, skip_server_check=True)
            self._server_started = False
            
            # Wait a moment for cleanup
            import asyncio
            await asyncio.sleep(0.5)
            
            # Start server
            logger.info("Starting ADB server...")
            await self._start_server()
            
            return True
        except Exception as e:
            logger.error(f"Failed to restart ADB server: {e}")
            return False
    
    async def get_devices(self) -> List[Dict[str, str]]:
        """
        Get list of connected devices
        
        Returns:
            List of device dictionaries with 'serial' and 'state' keys
        """
        stdout, _, _ = await self.execute(["devices", "-l"])
        
        devices = []
        for line in stdout.strip().split('\n')[1:]:  # Skip header
            if not line.strip():
                continue
            
            parts = line.split()
            if len(parts) < 2:
                continue
            
            serial = parts[0]
            state = parts[1]
            
            # Parse additional info (model, device name, etc.)
            info = {}
            for part in parts[2:]:
                if ':' in part:
                    key, value = part.split(':', 1)
                    info[key] = value
            
            devices.append({
                'serial': serial,
                'state': state,
                **info
            })
        
        logger.info(f"Found {len(devices)} device(s)")
        return devices
    
    async def get_device_info(self, device: str) -> Dict[str, str]:
        """
        Get detailed information about a device
        
        Args:
            device: Device serial number
        
        Returns:
            Dictionary with device properties
        """
        props = {}
        
        # Get common properties
        prop_keys = [
            "ro.product.model",
            "ro.product.manufacturer",
            "ro.build.version.release",
            "ro.build.version.sdk",
            "ro.product.cpu.abi"
        ]
        
        for key in prop_keys:
            try:
                stdout, _, _ = await self.execute(
                    ["shell", "getprop", key],
                    device=device
                )
                props[key] = stdout.strip()
            except Exception as e:
                logger.warning(f"Failed to get property {key}: {e}")
        
        return props
    
    async def pair_wireless(self, ip: str, port: int, code: str) -> bool:
        """
        Pair with a device for wireless debugging (Android 11+)
        
        Args:
            ip: Device IP address
            port: Pairing port (shown in Wireless Debugging settings)
            code: 6-digit pairing code
        
        Returns:
            True if pairing successful
        """
        try:
            stdout, _, _ = await self.execute(
                ["pair", f"{ip}:{port}", code],
                timeout=30
            )
            return "successfully paired" in stdout.lower()
        except Exception as e:
            logger.error(f"Wireless pairing failed: {e}")
            return False
    
    async def connect_wireless(self, ip: str, port: int = 5555) -> bool:
        """
        Connect to a device wirelessly
        
        Args:
            ip: Device IP address
            port: ADB port (default: 5555)
        
        Returns:
            True if connection successful
        """
        try:
            stdout, _, _ = await self.execute(["connect", f"{ip}:{port}"])
            return "connected" in stdout.lower()
        except Exception as e:
            logger.error(f"Wireless connection failed: {e}")
            return False
    
    async def disconnect_wireless(self, ip: str, port: int = 5555) -> bool:
        """
        Disconnect from a wireless device
        
        Args:
            ip: Device IP address
            port: ADB port (default: 5555)
        
        Returns:
            True if disconnection successful
        """
        try:
            await self.execute(["disconnect", f"{ip}:{port}"])
            return True
        except Exception as e:
            logger.error(f"Wireless disconnection failed: {e}")
            return False
    
    async def push_file(
        self,
        local_path: Path,
        remote_path: str,
        device: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Push a file to the device
        
        Args:
            local_path: Local file path
            remote_path: Remote file path on device
            device: Device serial number
            progress_callback: Optional callback(bytes_transferred, total_bytes)
        
        Returns:
            True if push successful
        """
        try:
            # For now, simple push without progress tracking
            # TODO: Implement progress tracking by parsing ADB output
            await self.execute(
                ["push", str(local_path), remote_path],
                device=device,
                timeout=300  # 5 minutes for large files
            )
            return True
        except Exception as e:
            logger.error(f"File push failed: {e}")
            return False
    
    async def pull_file(
        self,
        remote_path: str,
        local_path: Path,
        device: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Pull a file from the device
        
        Args:
            remote_path: Remote file path on device
            local_path: Local file path
            device: Device serial number
            progress_callback: Optional callback(bytes_transferred, total_bytes)
        
        Returns:
            True if pull successful
        """
        try:
            await self.execute(
                ["pull", remote_path, str(local_path)],
                device=device,
                timeout=300
            )
            return True
        except Exception as e:
            logger.error(f"File pull failed: {e}")
            return False
    
    async def install_apk(
        self,
        apk_path: Path,
        device: str,
        options: Optional[List[str]] = None
    ) -> bool:
        """
        Install an APK on the device
        
        Args:
            apk_path: Path to APK file
            device: Device serial number
            options: Additional install options (e.g., ['-r'] for reinstall)
        
        Returns:
            True if installation successful
        """
        try:
            args = ["install"]
            if options:
                args.extend(options)
            args.append(str(apk_path))
            
            stdout, _, _ = await self.execute(
                args,
                device=device,
                timeout=120
            )
            
            return "Success" in stdout
        except Exception as e:
            logger.error(f"APK installation failed: {e}")
            return False
    
    async def uninstall_package(self, package: str, device: str) -> bool:
        """
        Uninstall a package from the device
        
        Args:
            package: Package name
            device: Device serial number
        
        Returns:
            True if uninstallation successful
        """
        try:
            stdout, _, _ = await self.execute(
                ["uninstall", package],
                device=device
            )
            return "Success" in stdout
        except Exception as e:
            logger.error(f"Package uninstallation failed: {e}")
            return False
    
    async def shell(self, command: str, device: str) -> str:
        """
        Execute a shell command on the device
        
        Args:
            command: Shell command to execute
            device: Device serial number
        
        Returns:
            Command output
        """
        stdout, _, _ = await self.execute(
            ["shell", command],
            device=device
        )
        return stdout
