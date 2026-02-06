"""
Logcat Streamer - Real-time logcat streaming with filtering

This module handles real-time streaming of Android logcat output with
filtering and search capabilities.
"""

import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime
from PySide6.QtCore import QObject, Signal

from utils.adb_wrapper import ADBWrapper

logger = logging.getLogger(__name__)


class LogcatStreamer(QObject):
    """
    Streams logcat output from Android devices
    
    Signals:
        log_entry: Emitted for each log line (dict with timestamp, level, tag, message)
        streaming_started: Emitted when streaming starts
        streaming_stopped: Emitted when streaming stops
    """
    
    log_entry = Signal(dict)  # {timestamp, level, tag, pid, message}
    streaming_started = Signal()
    streaming_stopped = Signal()
    
    LEVELS = ['V', 'D', 'I', 'W', 'E', 'F']
    
    def __init__(self, adb: ADBWrapper):
        """
        Initialize Logcat Streamer
        
        Args:
            adb: ADB wrapper instance
        """
        super().__init__()
        self.adb = adb
        self._streaming = False
        self._stream_task: Optional[asyncio.Task] = None
        self._filters: Dict[str, str] = {}
        logger.info("Logcat Streamer initialized")
    
    async def start_streaming(
        self,
        device: str,
        filters: Optional[Dict[str, str]] = None
    ):
        """
        Start streaming logcat output
        
        Args:
            device: Device serial number
            filters: Optional filters dict with keys: level, tag, package
        """
        if self._streaming:
            logger.warning("Logcat streaming already active")
            return
        
        self._streaming = True
        self._filters = filters or {}
        
        cmd = ["logcat", "-v", "time"]
        
        if 'level' in self._filters:
            level = self._filters['level']
            cmd.extend(["-s", f"*:{level}"])
        
        if 'tag' in self._filters:
            tag = self._filters['tag']
            cmd.extend(["-s", f"{tag}:*"])
        
        logger.info(f"Starting logcat stream with filters: {self._filters}")
        
        self._stream_task = asyncio.ensure_future(
            self._stream_logcat(device, cmd)
        )
        
        self.streaming_started.emit()
    
    async def _stream_logcat(self, device: str, cmd: list):
        """
        Internal method to stream logcat output
        
        Args:
            device: Device serial number
            cmd: Logcat command arguments
        """
        process = None
        try:
            full_cmd = [str(self.adb.adb_path), "-s", device] + cmd
            
            # Prepare subprocess args
            kwargs = {
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

            process = await asyncio.create_subprocess_exec(
                *full_cmd,
                **kwargs
            )
            
            while self._streaming and process.stdout:
                line = await process.stdout.readline()
                if not line:
                    break
                
                try:
                    line_str = line.decode('utf-8', errors='replace').strip()
                    if not line_str:
                        continue
                    
                    entry = self._parse_log_line(line_str)
                    if entry:
                        if 'package' in self._filters:
                            package = self._filters['package']
                            if package not in entry.get('tag', ''):
                                continue
                        
                        self.log_entry.emit(entry)
                
                except Exception as e:
                    logger.debug(f"Failed to parse log line: {e}")
        
        except asyncio.CancelledError:
            logger.debug("Logcat streaming cancelled")
        except Exception as e:
            logger.error(f"Logcat streaming failed: {e}")
        finally:
            if process:
                try:
                    if process.stdout:
                        process.stdout.feed_eof()
                except Exception:
                    pass
                try:
                    if process.stderr:
                        process.stderr.feed_eof()
                except Exception:
                    pass
                
                if process.returncode is None:
                    try:
                        process.terminate()
                    except Exception:
                        pass
                    try:
                        process.kill()
                    except Exception:
                        pass
            
            self._streaming = False
            self.streaming_stopped.emit()
    
    def _parse_log_line(self, line: str) -> Optional[Dict[str, str]]:
        """
        Parse a logcat line into structured data
        
        Args:
            line: Raw logcat line
        
        Returns:
            Dict with parsed fields or None if parsing fails
        """
        try:
            # Format for -v time: MM-DD HH:MM:SS.mmm LEVEL/TAG( PID): MESSAGE
            # Example: 02-05 12:34:52.089 W/libperfmgr( 1234): Failed/write to node
            
            if len(line) < 20:
                return None
            
            timestamp = line[:18].strip()
            rest = line[18:].strip()
            
            if not rest:
                return None
            
            level = rest[0] if rest else 'I'
            
            if len(rest) < 2 or rest[1] != '/':
                return self._parse_threadtime(line)
            
            rest_after_slash = rest[2:]  # Skip "X/"
            
            paren_pos = rest_after_slash.find('(')
            colon_pos = rest_after_slash.find(':')
            
            pid = ''
            if paren_pos != -1 and paren_pos < colon_pos:
                tag = rest_after_slash[:paren_pos].strip()
                paren_end = rest_after_slash.find(')', paren_pos)
                if paren_end != -1:
                    pid = rest_after_slash[paren_pos+1:paren_end].strip()
                    message_start = rest_after_slash.find(':', paren_end)
                    if message_start != -1:
                        message = rest_after_slash[message_start+1:].strip()
                    else:
                        message = rest_after_slash[paren_end+1:].strip()
                else:
                    message = rest_after_slash[paren_pos:].strip()
            elif colon_pos != -1:
                tag = rest_after_slash[:colon_pos].strip()
                message = rest_after_slash[colon_pos+1:].strip()
            else:
                tag = rest_after_slash.strip()
                message = ''
            
            return {
                'timestamp': timestamp,
                'pid': pid,
                'tid': '',
                'level': level,
                'tag': tag,
                'message': message
            }
            
        except Exception as e:
            logger.debug(f"Log line parse error: {e}")
            return None
    
    def _parse_threadtime(self, line: str) -> Optional[Dict[str, str]]:
        """Parse threadtime format as fallback"""
        try:
            if len(line) < 30:
                return None
            timestamp = line[:18]
            rest = line[18:].strip()
            parts = rest.split(None, 4)
            if len(parts) < 5:
                return None
            pid, tid, level = parts[0], parts[1], parts[2]
            tag_and_msg = parts[4]
            if ':' in tag_and_msg:
                tag, message = tag_and_msg.split(':', 1)
            else:
                tag, message = '', tag_and_msg
            return {
                'timestamp': timestamp,
                'pid': pid,
                'tid': tid,
                'level': level,
                'tag': tag.strip(),
                'message': message.strip()
            }
        except Exception:
            return None

    
    async def stop_streaming(self):
        """Stop streaming logcat output"""
        if not self._streaming:
            return
        
        logger.info("Stopping logcat stream")
        self._streaming = False
        
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None
    
    def set_filter(
        self,
        level: Optional[str] = None,
        tag: Optional[str] = None,
        package: Optional[str] = None
    ):
        """
        Update filters (requires restart of streaming)
        
        Args:
            level: Log level filter (V, D, I, W, E, F)
            tag: Tag filter
            package: Package name filter
        """
        if level:
            self._filters['level'] = level
        if tag:
            self._filters['tag'] = tag
        if package:
            self._filters['package'] = package
        
        logger.info(f"Updated filters: {self._filters}")
    
    def clear_filters(self):
        """Clear all filters"""
        self._filters.clear()
        logger.info("Cleared all filters")
    
    async def export_logs(self, device: str, output_path: str) -> bool:
        """
        Export logcat to a file
        
        Args:
            device: Device serial number
            output_path: Output file path
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Exporting logcat to {output_path}")
            
            output = await self.adb.shell("logcat -d", device)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output)
            
            logger.info(f"Successfully exported logcat to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export logcat: {e}")
            return False
    
    def is_streaming(self) -> bool:
        """Check if currently streaming"""
        return self._streaming
