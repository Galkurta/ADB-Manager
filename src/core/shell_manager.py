"""
Shell Manager - Interactive ADB shell session management

This module handles interactive ADB shell sessions with command execution,
output streaming, and history tracking.
"""

import asyncio
import logging
from typing import Optional, List
from PySide6.QtCore import QObject, Signal

from utils.adb_wrapper import ADBWrapper

logger = logging.getLogger(__name__)


class ShellManager(QObject):
    """
    Manages interactive ADB shell sessions
    
    Signals:
        output_received: Emitted when output is received (output: str, is_error: bool)
        shell_started: Emitted when shell session starts
        shell_stopped: Emitted when shell session stops
        shell_error: Emitted on shell errors (error_message: str)
    """
    
    output_received = Signal(str, bool)  # (output, is_error)
    shell_started = Signal()
    shell_stopped = Signal()
    shell_error = Signal(str)
    
    def __init__(self, adb: ADBWrapper):
        """
        Initialize Shell Manager
        
        Args:
            adb: ADB wrapper instance
        """
        super().__init__()
        self.adb = adb
        self._active = False
        self._process: Optional[asyncio.subprocess.Process] = None
        self._read_task: Optional[asyncio.Task] = None
        self._current_device: Optional[str] = None
        self._command_history: List[str] = []
        self._history_index = -1
        logger.info("Shell Manager initialized")
    
    async def start_shell(self, device: str):
        """
        Start interactive shell session
        
        Args:
            device: Device serial number
        """
        if self._active:
            logger.warning("Shell already active")
            return
        
        try:
            self._current_device = device
            
            cmd = [str(self.adb.adb_path), "-s", device, "shell"]
            
            logger.info(f"Starting shell session for device {device}")
            
            # Prepare subprocess args
            kwargs = {
                'stdin': asyncio.subprocess.PIPE,
                'stdout': asyncio.subprocess.PIPE,
                'stderr': asyncio.subprocess.PIPE
            }
            
            import sys
            import subprocess
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                kwargs['startupinfo'] = startupinfo

            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                **kwargs
            )
            
            self._active = True
            
            self._read_task = asyncio.ensure_future(self._read_output())
            
            self.shell_started.emit()
            logger.info("Shell session started")
            
        except Exception as e:
            error_msg = f"Failed to start shell: {e}"
            logger.error(error_msg)
            self.shell_error.emit(error_msg)
            self._active = False
    
    async def _read_output(self):
        """Read and emit shell output"""
        try:
            while self._active and self._process:
                if self._process.stdout:
                    try:
                        # Use wait_for with timeout to avoid blocking forever
                        line = await asyncio.wait_for(
                            self._process.stdout.readline(),
                            timeout=0.1
                        )
                        if line:
                            output = line.decode('utf-8', errors='replace')
                            self.output_received.emit(output, False)
                    except asyncio.TimeoutError:
                        pass
                
                if self._process.stderr:
                    try:
                        line = await asyncio.wait_for(
                            self._process.stderr.readline(),
                            timeout=0.1
                        )
                        if line:
                            output = line.decode('utf-8', errors='replace')
                            self.output_received.emit(output, True)
                    except asyncio.TimeoutError:
                        pass
                
                await asyncio.sleep(0.01)
        
        except asyncio.CancelledError:
            logger.debug("Shell read task cancelled")
        except Exception as e:
            logger.error(f"Error reading shell output: {e}")
        finally:
            if self._active:
                self._active = False
                self.shell_stopped.emit()
    
    async def execute_command(self, command: str):
        """
        Execute command in shell
        
        Args:
            command: Command to execute
        """
        if not self._active or not self._process or not self._process.stdin:
            logger.warning("Shell not active")
            return
        
        try:
            if command.strip() and (not self._command_history or self._command_history[-1] != command):
                self._command_history.append(command)
            self._history_index = len(self._command_history)
            
            self._process.stdin.write((command + '\n').encode('utf-8'))
            await self._process.stdin.drain()
            
            logger.debug(f"Executed command: {command}")
            
        except Exception as e:
            error_msg = f"Failed to execute command: {e}"
            logger.error(error_msg)
            self.shell_error.emit(error_msg)
    
    async def stop_shell(self):
        """Stop shell session"""
        if not self._active:
            return
        
        logger.info("Stopping shell session")
        self._active = False
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None
        
        if self._process:
            if self._process.returncode is None:
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    self._process.kill()
                    await self._process.wait()
            self._process = None
        
        self.shell_stopped.emit()
        logger.info("Shell session stopped")
    
    def get_history(self) -> List[str]:
        """
        Get command history
        
        Returns:
            List of previous commands
        """
        return self._command_history.copy()
    
    def get_history_prev(self) -> Optional[str]:
        """
        Get previous command from history
        
        Returns:
            Previous command or None
        """
        if not self._command_history:
            return None
        
        if self._history_index > 0:
            self._history_index -= 1
        
        if 0 <= self._history_index < len(self._command_history):
            return self._command_history[self._history_index]
        
        return None
    
    def get_history_next(self) -> Optional[str]:
        """
        Get next command from history
        
        Returns:
            Next command or None
        """
        if not self._command_history:
            return None
        
        if self._history_index < len(self._command_history):
            self._history_index += 1
        
        if self._history_index < len(self._command_history):
            return self._command_history[self._history_index]
        
        return ""
    
    def reset_history_index(self):
        """Reset history navigation index"""
        self._history_index = len(self._command_history)
    
    def is_active(self) -> bool:
        """Check if shell is active"""
        return self._active
    
    def get_current_device(self) -> Optional[str]:
        """Get current device serial"""
        return self._current_device
