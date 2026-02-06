"""
File Manager - File system operations with progress tracking

This module handles device file system operations including listing,
transferring, and managing files and directories.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal

from utils.adb_wrapper import ADBWrapper

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Represents a file or directory on the device"""
    name: str
    path: str
    is_directory: bool
    size: int = 0
    permissions: str = ""
    modified_time: str = ""
    
    @property
    def display_size(self) -> str:
        """Get human-readable file size"""
        if self.is_directory:
            return "<DIR>"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.size < 1024.0:
                return f"{self.size:.1f} {unit}"
            self.size /= 1024.0
        return f"{self.size:.1f} TB"


class FileManager(QObject):
    """
    Manages file operations on Android devices
    
    Signals:
        transfer_progress: Emitted during file transfers (bytes_transferred, total_bytes, filename)
        transfer_complete: Emitted when transfer completes (success, filename)
    """
    
    transfer_progress = Signal(int, int, str)  # bytes_transferred, total_bytes, filename
    transfer_complete = Signal(bool, str)  # success, filename
    
    def __init__(self, adb: ADBWrapper):
        """
        Initialize File Manager
        
        Args:
            adb: ADB wrapper instance
        """
        super().__init__()
        self.adb = adb
        logger.info("File Manager initialized")
    
    async def list_directory(self, device: str, path: str) -> List[FileInfo]:
        """
        List contents of a directory on the device
        
        Args:
            device: Device serial number
            path: Directory path to list
        
        Returns:
            List of FileInfo objects
        """
        try:
            if not path.endswith('/'):
                path = path + '/'
            
            logger.info(f"FileManager: Listing directory {path} on device {device}")
            
            output = await self.adb.shell(f"ls -la {path}", device)
            
            logger.debug(f"FileManager: ls output length: {len(output)} chars")
            
            files = []
            for line in output.strip().split('\n'):
                line = line.strip()  # Remove \r and other whitespace
                if not line or line.startswith('total'):
                    continue
                
                # Android ls -la format: perms links owner group size date time name
                # Example: drwxrws--- 2 u0_a209 media_rw 3452 2026-02-05 08:56 Alarms
                parts = line.split(None, 7)  # Split into max 8 parts
                if len(parts) < 8:
                    print(f">>> FILE_MANAGER: Skipping line (only {len(parts)} parts): {line[:50]}")
                    continue
                
                permissions = parts[0]
                size_str = parts[4]
                name = parts[7]  # Name is the 8th column (index 7)
                
                if name in ['.', '..']:
                    continue
                
                is_dir = permissions.startswith('d')
                size = 0 if is_dir else int(size_str) if size_str.isdigit() else 0
                
                file_path = f"{path}{name}"
                
                files.append(FileInfo(
                    name=name,
                    path=file_path,
                    is_directory=is_dir,
                    size=size,
                    permissions=permissions
                ))
            
            logger.info(f"FileManager: Listed {len(files)} items in {path}")
            return files
            
        except Exception as e:
            logger.error(f"FileManager: Failed to list directory {path}: {e}")
            return []
    
    async def push_file(
        self,
        device: str,
        local_path: Path,
        remote_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Push a file to the device
        
        Args:
            device: Device serial number
            local_path: Local file path
            remote_path: Remote destination path
            progress_callback: Optional callback(bytes_transferred, total_bytes)
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Pushing {local_path} to {remote_path}")
            
            file_size = local_path.stat().st_size
            self.transfer_progress.emit(0, file_size, local_path.name)
            
            success = await self.adb.push_file(
                local_path,
                remote_path,
                device,
                progress_callback
            )
            
            self.transfer_complete.emit(success, local_path.name)
            
            if success:
                logger.info(f"Successfully pushed {local_path.name}")
            else:
                logger.error(f"Failed to push {local_path.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Push file failed: {e}")
            self.transfer_complete.emit(False, local_path.name)
            return False
    
    async def pull_file(
        self,
        device: str,
        remote_path: str,
        local_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Pull a file from the device
        
        Args:
            device: Device serial number
            remote_path: Remote file path
            local_path: Local destination path
            progress_callback: Optional callback(bytes_transferred, total_bytes)
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Pulling {remote_path} to {local_path}")
            
            self.transfer_progress.emit(0, 0, Path(remote_path).name)
            
            success = await self.adb.pull_file(
                remote_path,
                local_path,
                device,
                progress_callback
            )
            
            self.transfer_complete.emit(success, Path(remote_path).name)
            
            if success:
                logger.info(f"Successfully pulled {Path(remote_path).name}")
            else:
                logger.error(f"Failed to pull {Path(remote_path).name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Pull file failed: {e}")
            self.transfer_complete.emit(False, Path(remote_path).name)
            return False
    
    async def delete_file(self, device: str, path: str) -> bool:
        """
        Delete a file or directory from the device
        
        Args:
            device: Device serial number
            path: Path to delete
        
        Returns:
            True if successful
        """
        try:
            await self.adb.shell(f"rm -rf '{path}'", device)
            logger.info(f"Deleted {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return False
    
    async def create_directory(self, device: str, path: str) -> bool:
        """
        Create a directory on the device
        
        Args:
            device: Device serial number
            path: Directory path to create
        
        Returns:
            True if successful
        """
        try:
            await self.adb.shell(f"mkdir -p '{path}'", device)
            logger.info(f"Created directory {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False
    
    async def chmod(self, device: str, path: str, permissions: str) -> bool:
        """
        Change file permissions
        
        Args:
            device: Device serial number
            path: File path
            permissions: Permission string (e.g., '755', '644')
        
        Returns:
            True if successful
        """
        try:
            await self.adb.shell(f"chmod {permissions} '{path}'", device)
            logger.info(f"Changed permissions of {path} to {permissions}")
            return True
        except Exception as e:
            logger.error(f"Failed to chmod {path}: {e}")
            return False
