"""
Logcat Viewer Widget - View real-time device logs

This widget provides an interface for viewing and filtering logcat output.
"""

import asyncio
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QComboBox, QLineEdit, QLabel, QFileDialog
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCursor, QColor, QFont

from core.logcat_streamer import LogcatStreamer
from utils.async_helper import safe_ensure_future
from utils.ui_utils import show_warning, show_info

logger = logging.getLogger(__name__)


class LogcatViewerWidget(QWidget):
    """Logcat viewer widget for displaying device logs"""
    
    LEVEL_COLORS = {
        'V': QColor(158, 158, 158),   # Verbose - Gray
        'D': QColor(33, 150, 243),    # Debug - Blue
        'I': QColor(76, 175, 80),     # Info - Green
        'W': QColor(255, 193, 7),     # Warning - Amber
        'E': QColor(244, 67, 54),     # Error - Red
        'A': QColor(156, 39, 176),    # Assert - Purple
        'F': QColor(156, 39, 176)     # Fatal - Purple
    }
    
    LEVEL_NAMES = {
        'V': 'VERBOSE',
        'D': 'DEBUG',
        'I': 'INFO',
        'W': 'WARN',
        'E': 'ERROR',
        'A': 'ASSERT',
        'F': 'FATAL'
    }

    def __init__(self, logcat_streamer: LogcatStreamer):
        """
        Initialize Logcat Viewer Widget
        
        Args:
            logcat_streamer: LogcatStreamer instance
        """
        super().__init__()
        self.logcat_streamer = logcat_streamer
        self.current_device = None
        
        self._log_buffer = []
        self._max_buffer_size = 10000
        
        self._user_scrolled_up = False
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        
        filter_layout.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["All", "VERBOSE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"])
        self.level_combo.setCurrentText("INFO")  # Default to INFO
        self.level_combo.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.level_combo)
        
        filter_layout.addWidget(QLabel("Tag:"))
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("Filter by tag...")
        self.tag_edit.textChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.tag_edit)
        
        filter_layout.addWidget(QLabel("Package:"))
        self.package_edit = QLineEdit()
        self.package_edit.setPlaceholderText("Filter by package...")
        self.package_edit.textChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.package_edit)
        
        layout.addLayout(filter_layout)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.log_display.setFont(font)
        
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                padding: 2px;
                line-height: 1.0;
            }
        """)
        
        self.log_display.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        layout.addWidget(self.log_display)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self._start_streaming_slot)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_streaming)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_logs)
        button_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._export_logs)
        button_layout.addWidget(self.export_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect logcat streamer signals"""
        self.logcat_streamer.log_entry.connect(self._add_log_entry)
        self.logcat_streamer.streaming_started.connect(self._on_streaming_started)
        self.logcat_streamer.streaming_stopped.connect(self._on_streaming_stopped)
    
    def set_device(self, device: str):
        """
        Set current device
        
        Args:
            device: Device serial number
        """
        self.current_device = device
        if self.logcat_streamer.is_streaming():
            asyncio.ensure_future(self._restart_streaming())
    
    async def _restart_streaming(self):
        """Restart streaming with new device"""
        await self.logcat_streamer.stop_streaming()
        await self._start_streaming()
    
    def _get_current_level_filter(self) -> str:
        """Get the current level filter as single letter"""
        level_text = self.level_combo.currentText()
        if level_text == "All":
            return None
        for letter, name in self.LEVEL_NAMES.items():
            if name == level_text:
                return letter
        return None
    
    def _entry_passes_filter(self, entry: dict) -> bool:
        """Check if a log entry passes the current filters"""
        level_filter = self._get_current_level_filter()
        tag_filter = self.tag_edit.text().strip().lower()
        package_filter = self.package_edit.text().strip().lower()
        
        entry_level = entry.get('level', 'I')
        entry_tag = entry.get('tag', '').lower()
        entry_message = entry.get('message', '').lower()
        
        if level_filter and entry_level != level_filter:
            return False
        
        if tag_filter and tag_filter not in entry_tag:
            return False
        
        if package_filter:
            if package_filter not in entry_tag and package_filter not in entry_message:
                return False
        
        return True
    
    def _format_log_entry(self, entry: dict) -> str:
        """Format a log entry for display with aligned columns"""
        timestamp = entry.get('timestamp', '')
        level = entry.get('level', 'I')
        tag = entry.get('tag', '')
        message = entry.get('message', '')
        pid = entry.get('pid', '')
        
        level_name = self.LEVEL_NAMES.get(level, level)
        level_str = f"[{level_name}]"
        
        TAG_WIDTH = 20
        if len(tag) > TAG_WIDTH:
            tag_str = tag[:TAG_WIDTH-1] + "…"  # Truncate with ellipsis
        else:
            tag_str = tag.ljust(TAG_WIDTH)  # Pad with spaces
        
        if pid:
            return f"[{timestamp}] {pid:>5} {level_str:>9} {tag_str} : {message}"
        else:
            return f"[{timestamp}]       {level_str:>9} {tag_str} : {message}"
    
    def _on_scroll(self):
        """Handle scroll event for smart autoscroll"""
        scrollbar = self.log_display.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
        self._user_scrolled_up = not at_bottom
    
    def _on_filter_changed(self):
        """Handle filter change - refilter existing buffer"""
        self._refresh_display_from_buffer()
    
    def _refresh_display_from_buffer(self):
        """Refresh the display by refiltering the buffer"""
        self.log_display.clear()
        
        for entry in self._log_buffer:
            if self._entry_passes_filter(entry):
                self._display_entry(entry, auto_scroll=False)
        
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )
        self._user_scrolled_up = False
    
    def _display_entry(self, entry: dict, auto_scroll: bool = True):
        """Display a single log entry"""
        level = entry.get('level', 'I')
        log_line = self._format_log_entry(entry)
        
        color = self.LEVEL_COLORS.get(level, QColor(212, 212, 212))
        
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        format = cursor.charFormat()
        format.setForeground(color)
        cursor.setCharFormat(format)
        
        cursor.insertText(log_line + '\n')
        
        if auto_scroll and not self._user_scrolled_up:
            self.log_display.setTextCursor(cursor)
            self.log_display.ensureCursorVisible()
    
    @Slot()
    def _start_streaming_slot(self):
        """Slot wrapper for start button"""
        self._apply_filters_to_streamer()
        safe_ensure_future(self._start_streaming())
    
    async def _start_streaming(self):
        """Start logcat streaming"""
        if not self.current_device:
            show_warning(self, "ADB Manager", "No device selected")
            return
        
        try:
            await self.logcat_streamer.start_streaming(self.current_device)
        except Exception as e:
            logger.error(f"Failed to start logcat: {e}")

    def _apply_filters_to_streamer(self):
        """Apply current UI filters to the logcat streamer"""
        level = self._get_current_level_filter()
        package = self.package_edit.text().strip()
        
        self.logcat_streamer.clear_filters()
        
        if level:
            self.logcat_streamer.set_filter(level=level)
        if package:
            self.logcat_streamer.set_filter(package=package)
    
    @Slot()
    def _stop_streaming(self):
        """Stop logcat streaming"""
        safe_ensure_future(self.logcat_streamer.stop_streaming())
    
    @Slot(dict)
    def _add_log_entry(self, entry: dict):
        """
        Add log entry to display
        
        Args:
            entry: Log entry dict with timestamp, level, tag, message
        """
        self._log_buffer.append(entry)
        
        if len(self._log_buffer) > self._max_buffer_size:
            self._log_buffer = self._log_buffer[-self._max_buffer_size:]
        
        if self._entry_passes_filter(entry):
            self._display_entry(entry)
    
    def _clear_logs(self):
        """Clear logs and buffer"""
        self._log_buffer.clear()
        self.log_display.clear()
        self._user_scrolled_up = False
    
    @Slot()
    def _on_streaming_started(self):
        """Handle streaming started"""
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._display_system_message("=== Logcat streaming started ===")
    
    @Slot()
    def _on_streaming_stopped(self):
        """Handle streaming stopped"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._display_system_message("=== Logcat streaming stopped ===")
    
    def _display_system_message(self, message: str):
        """Display a system message in gray"""
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        format = cursor.charFormat()
        format.setForeground(QColor(128, 128, 128))
        cursor.setCharFormat(format)
        
        cursor.insertText(message + '\n')
        
        if not self._user_scrolled_up:
            self.log_display.setTextCursor(cursor)
            self.log_display.ensureCursorVisible()
    
    @Slot()
    def _export_logs(self):
        """Export logs to file"""
        if not self.current_device:
            show_warning(self, "ADB Manager", "No device selected")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", "logcat.txt", "Text Files (*.txt)"
        )
        if not file_path:
            return
        
        asyncio.ensure_future(self._do_export(file_path))
    
    async def _do_export(self, file_path: str):
        """Perform export operation"""
        success = await self.logcat_streamer.export_logs(
            self.current_device, file_path
        )
        if success:
            show_info(self, "ADB Manager", "Logs exported successfully")
        else:
            show_warning(self, "ADB Manager", "Failed to export logs")

