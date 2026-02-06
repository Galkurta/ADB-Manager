"""
Mirror Engine - Screen mirroring integration with scrcpy

Provides screen mirroring functionality using scrcpy subprocess.
"""

import logging
import asyncio
import shutil
from pathlib import Path
from typing import Optional, Dict
from PySide6.QtCore import QObject, Signal, QSettings, QTimer

logger = logging.getLogger(__name__)


class MirrorEngine(QObject):
    """Screen mirroring engine using scrcpy"""
    
    mirror_started = Signal()
    mirror_stopped = Signal()
    error_occurred = Signal(str)
    
    def __init__(self):
        """Initialize Mirror Engine"""
        super().__init__()
        self._process: Optional[asyncio.subprocess.Process] = None
        self._device: Optional[str] = None
        self.settings = QSettings('ADBManager', 'ADBManager')
        
        # Timer for monitoring process (avoids async conflicts with qasync)
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._check_process_status)
        self._monitor_timer.setInterval(200)  # Check every 200ms
    
    def is_scrcpy_available(self) -> bool:
        """
        Check if scrcpy is available in PATH or custom path
        
        Returns:
            True if scrcpy is found, False otherwise
        """
        custom_path = self.settings.value('scrcpy_path', '')
        if custom_path:
            scrcpy_exe = Path(custom_path) / 'scrcpy.exe'
            if scrcpy_exe.exists():
                return True
        
        return shutil.which('scrcpy') is not None
    
    def _get_scrcpy_command(self) -> str:
        """
        Get scrcpy executable path
        
        Returns:
            Path to scrcpy executable
        """
        custom_path = self.settings.value('scrcpy_path', '')
        if custom_path:
            scrcpy_exe = Path(custom_path) / 'scrcpy.exe'
            if scrcpy_exe.exists():
                return str(scrcpy_exe)
        
        return 'scrcpy'
    
    async def start_mirror(self, device: str, options: Optional[Dict] = None) -> bool:
        """
        Start screen mirroring
        
        Args:
            device: Device serial number
            options: Optional mirroring options
                - resolution: str (e.g., '1280x720')
                - bitrate: int (Mbps)
                - max_fps: int
                - always_on_top: bool
                - fullscreen: bool
                
        Returns:
            True if started successfully, False otherwise
        """
        if self._process:
            logger.warning("Mirroring already active")
            return False
        
        if not self.is_scrcpy_available():
            error_msg = "scrcpy not found. Please install scrcpy and add it to PATH."
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
        
        scrcpy_cmd = self._get_scrcpy_command()
        cmd = [scrcpy_cmd, '-s', device]
        
        if options:
            if 'resolution' in options and options['resolution'] != 'Auto':
                cmd.extend(['-m', options['resolution'].split('x')[0]])  # Max size
            
            if 'bitrate' in options:
                cmd.extend(['-b', f"{options['bitrate']}M"])
            
            if 'max_fps' in options:
                cmd.extend(['--max-fps', str(options['max_fps'])])
            
            if options.get('always_on_top', False):
                cmd.append('--always-on-top')
            
            if options.get('fullscreen', False):
                cmd.append('--fullscreen')
        
        try:
            logger.info(f"Starting scrcpy: {' '.join(cmd)}")
            
            # Prepare subprocess arguments
            kwargs = {
                'stdout': asyncio.subprocess.PIPE,
                'stderr': asyncio.subprocess.PIPE
            }
            
            # On Windows, use DETACHED_PROCESS to prevent console inheritance
            # but allow scrcpy's SDL GUI window to appear normally
            import sys
            import subprocess
            if sys.platform == 'win32':
                kwargs['creationflags'] = subprocess.DETACHED_PROCESS
            
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                **kwargs
            )
            
            self._device = device
            self.mirror_started.emit()
            logger.info(f"Screen mirroring started for {device}")
            
            self._monitor_timer.start()
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to start mirroring: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    async def stop_mirror(self):
        """Stop screen mirroring"""
        if not self._process:
            return
        
        self._monitor_timer.stop()
        
        try:
            self._process.terminate()
            await asyncio.wait_for(self._process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            self._process.kill()
            await self._process.wait()
        except Exception as e:
            logger.error(f"Error stopping mirroring: {e}")
        finally:
            self._process = None
            self._device = None
            self.mirror_stopped.emit()
            logger.info("Screen mirroring stopped")
    
    def _check_process_status(self):
        """
        Timer callback: Check if scrcpy process is still running.
        Uses QTimer instead of async loop to avoid qasync conflicts.
        """
        if not self._process:
            self._monitor_timer.stop()
            return
        
        if self._process.returncode is not None:
            self._monitor_timer.stop()
            
            if self._process.returncode != 0:
                logger.error(f"scrcpy exited with code: {self._process.returncode}")
                self.error_occurred.emit("Screen mirroring ended unexpectedly")
            
            self._process = None
            self._device = None
            self.mirror_stopped.emit()
            logger.info("Screen mirroring stopped")
    
    async def take_screenshot(self, output_path: Path) -> bool:
        """
        Take a screenshot (requires scrcpy to be running)
        
        Args:
            output_path: Path to save screenshot
            
        Returns:
            True if successful, False otherwise
            
        Note:
            This is a placeholder. Actual screenshot functionality would require
            either using scrcpy's built-in screenshot feature or capturing via ADB.
        """
        if not self._device:
            logger.warning("No active mirroring session")
            return False
        
        # TODO: Implement screenshot via ADB screencap
        logger.info(f"Screenshot requested: {output_path}")
        return False
    
    async def start_recording(self, output_path: Path) -> bool:
        """
        Start screen recording
        
        Args:
            output_path: Path to save recording
            
        Returns:
            True if successful, False otherwise
            
        Note:
            This would require launching scrcpy with --record option or using ADB screenrecord
        """
        logger.info(f"Recording requested: {output_path}")
        # TODO: Implement recording
        return False
    
    async def stop_recording(self) -> bool:
        """
        Stop screen recording
        
        Returns:
            True if successful, False otherwise
        """
        # TODO: Implement recording stop
        return False
    
    @property
    def is_mirroring(self) -> bool:
        """Check if mirroring is active"""
        return self._process is not None
    
    @property
    def current_device(self) -> Optional[str]:
        """Get currently mirrored device"""
        return self._device
