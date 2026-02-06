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
        self._using_vbs = False  # Track if we launched via VBS (can't monitor process)
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
            Path to scrcpy executable (prefers scrcpy-noconsole.vbs on Windows)
        """
        import sys
        
        custom_path = self.settings.value('scrcpy_path', '')
        logger.debug(f"scrcpy_path setting value: '{custom_path}'")
        
        if custom_path:
            custom_dir = Path(custom_path)
            
            # On Windows, prefer scrcpy-noconsole.vbs (VBS wrapper hides ALL consoles)
            if sys.platform == 'win32':
                # First try .vbs wrapper (best option - hides all console windows)
                noconsole_vbs = custom_dir / 'scrcpy-noconsole.vbs'
                if noconsole_vbs.exists():
                    logger.info(f"Using scrcpy-noconsole.vbs: {noconsole_vbs}")
                    return str(noconsole_vbs)
                
                # Fallback to .exe variant
                noconsole_exe = custom_dir / 'scrcpy-noconsole.exe'
                if noconsole_exe.exists():
                    logger.info(f"Using scrcpy-noconsole.exe: {noconsole_exe}")
                    return str(noconsole_exe)
            
            scrcpy_exe = custom_dir / 'scrcpy.exe'
            if scrcpy_exe.exists():
                logger.info(f"Using scrcpy.exe: {scrcpy_exe}")
                return str(scrcpy_exe)
        
        logger.info("Falling back to 'scrcpy' from PATH")
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
        # In VBS mode, we can't track the actual scrcpy process
        # Check if we think we're currently mirroring
        if self._process and not self._using_vbs:
            # Only block if we have a real process handle (not VBS mode)
            if self._process.returncode is None:
                logger.warning("Mirroring already active")
                return False
            else:
                # Process has exited, clean up
                self._process = None
        
        # Also check _using_vbs flag - if set but process is gone, reset it
        if self._using_vbs and self._process is None:
            self._using_vbs = False
        
        if not self.is_scrcpy_available():
            error_msg = "scrcpy not found. Please install scrcpy and add it to PATH."
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
        
        scrcpy_cmd = self._get_scrcpy_command()
        
        # Build scrcpy arguments
        scrcpy_args = ['-s', device]
        
        if options:
            if 'resolution' in options and options['resolution'] != 'Auto':
                scrcpy_args.extend(['-m', options['resolution'].split('x')[0]])  # Max size
            
            if 'bitrate' in options:
                scrcpy_args.extend(['-b', f"{options['bitrate']}M"])
            
            if 'max_fps' in options:
                scrcpy_args.extend(['--max-fps', str(options['max_fps'])])
            
            if options.get('always_on_top', False):
                scrcpy_args.append('--always-on-top')
            
            if options.get('fullscreen', False):
                scrcpy_args.append('--fullscreen')
        
        try:
            import sys
            import subprocess
            
            # Check if we're using a VBS wrapper
            if scrcpy_cmd.endswith('.vbs'):
                # VBS wrapper: The VBS file runs "cmd /c scrcpy.exe" from its directory
                # We need to set cwd to the scrcpy directory so it can find scrcpy.exe
                # NOTE: wscript.exe exits immediately after spawning scrcpy, so we can't monitor the process
                self._using_vbs = True
                scrcpy_dir = str(Path(scrcpy_cmd).parent)
                cmd_line = f'wscript.exe "{scrcpy_cmd}" {" ".join(scrcpy_args)}'
                logger.info(f"Starting scrcpy via VBS: {cmd_line} (cwd: {scrcpy_dir})")
                
                if sys.platform == 'win32':
                    # Use shell execution for VBS with correct working directory
                    self._process = await asyncio.create_subprocess_shell(
                        cmd_line,
                        cwd=scrcpy_dir,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
            else:
                # Regular executable - we can monitor this process
                self._using_vbs = False
                cmd = [scrcpy_cmd] + scrcpy_args
                logger.info(f"Starting scrcpy: {' '.join(cmd)}")
                
                kwargs = {}
                if sys.platform == 'win32':
                    kwargs['creationflags'] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                
                self._process = await asyncio.create_subprocess_exec(
                    *cmd,
                    **kwargs
                )
            
            self._device = device
            self.mirror_started.emit()
            logger.info(f"Screen mirroring started for {device}")
            
            # Only start monitor timer if we can actually track the process
            # VBS launches wscript which exits immediately - we can't monitor scrcpy itself
            if not self._using_vbs:
                self._monitor_timer.start()
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to start mirroring: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    async def stop_mirror(self):
        """Stop screen mirroring"""
        if not self._process and not self._using_vbs:
            return
        
        self._monitor_timer.stop()
        
        # If using VBS mode, we can't terminate via process handle
        # because wscript.exe has already exited. Use taskkill to find and kill scrcpy.exe
        if self._using_vbs:
            try:
                import subprocess
                # Use taskkill to terminate scrcpy.exe (only for this device session)
                # /F = Force, /IM = Image name
                result = subprocess.run(
                    ['taskkill', '/F', '/IM', 'scrcpy.exe'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    logger.info("scrcpy.exe terminated successfully")
                else:
                    logger.warning(f"taskkill returned: {result.stderr.strip()}")
            except Exception as e:
                logger.error(f"Failed to kill scrcpy: {e}")
            finally:
                self._process = None
                self._device = None
                self._using_vbs = False
                self.mirror_stopped.emit()
                logger.info("Screen mirroring stopped (VBS mode)")
            return
        
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
