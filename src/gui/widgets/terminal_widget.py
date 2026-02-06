"""
Terminal Widget - Interactive ADB shell interface

This widget provides a terminal-like interface for executing commands
on Android devices via ADB shell.
"""

import asyncio
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QTextCursor, QColor, QKeyEvent, QFont

from core.shell_manager import ShellManager
from utils.async_helper import safe_ensure_future
from utils.ui_utils import show_warning, show_info

logger = logging.getLogger(__name__)


class TerminalWidget(QWidget):
    """Terminal widget for interactive shell access"""
    
    def __init__(self, shell_manager: ShellManager):
        """
        Initialize Terminal Widget
        
        Args:
            shell_manager: ShellManager instance
        """
        super().__init__()
        self.shell_manager = shell_manager
        self.current_device = None
        self.current_path = "/"
        self.is_root = False
        self.last_command = ""
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Shell")
        self.start_btn.clicked.connect(self._start_shell_slot)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Shell")
        self.stop_btn.clicked.connect(self._stop_shell_slot)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_terminal)
        button_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._export_output)
        button_layout.addWidget(self.export_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.terminal_display = QTextEdit()
        self.terminal_display.setReadOnly(True)
        
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.terminal_display.setFont(font)
        
        self.terminal_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
        """)
        layout.addWidget(self.terminal_display)
        
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLineEdit())  # Placeholder for label
        input_layout.itemAt(0).widget().setText("Command:")
        input_layout.itemAt(0).widget().setReadOnly(True)
        input_layout.itemAt(0).widget().setMaximumWidth(80)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command...")
        self.command_input.returnPressed.connect(self._execute_command)
        self.command_input.installEventFilter(self)
        input_layout.addWidget(self.command_input)
        
        layout.addLayout(input_layout)
    
    def _connect_signals(self):
        """Connect shell manager signals"""
        self.shell_manager.output_received.connect(self._add_output)
        self.shell_manager.shell_started.connect(self._on_shell_started)
        self.shell_manager.shell_stopped.connect(self._on_shell_stopped)
        self.shell_manager.shell_error.connect(self._on_shell_error)
    
    def set_device(self, device: str):
        """
        Set current device
        
        Args:
            device: Device serial number
        """
        self.current_device = device
        
        if self.shell_manager.is_active():
            safe_ensure_future(self._restart_shell())
    
    async def _restart_shell(self):
        """Restart shell with new device"""
        await self.shell_manager.stop_shell()
        await self._start_shell()
    
    @Slot()
    def _start_shell_slot(self):
        """Slot wrapper for start button"""
        safe_ensure_future(self._start_shell())
    
    async def _start_shell(self):
        """Start shell session"""
        if not self.current_device:
            show_warning(self, "ADB Manager", "No device selected")
            return
        
        await self.shell_manager.start_shell(self.current_device)
    
    @Slot()
    def _stop_shell_slot(self):
        """Slot wrapper for stop button"""
        safe_ensure_future(self.shell_manager.stop_shell())
    
    @Slot()
    def _execute_command(self):
        """Execute command from input"""
        command = self.command_input.text().strip()
        if not command:
            return
        
        if not self.shell_manager.is_active():
            show_warning(self, "ADB Manager", "Shell not active")
            return
        
        self.last_command = command
        
        # Just display the command (prompt is already visible from shell start or previous command)
        self._add_text(command + '\n', QColor(220, 220, 220))
        
        if command.startswith('cd ') or command == 'cd':
            self._update_path_from_cd(command)
        
        safe_ensure_future(self._execute_and_prompt(command))
        
        self.command_input.clear()
        self.shell_manager.reset_history_index()
    
    async def _execute_and_prompt(self, command: str):
        """Execute command and show prompt after output"""
        await self.shell_manager.execute_command(command)
        await asyncio.sleep(0.5)
        self._add_prompt()

    
    def eventFilter(self, obj, event):
        """Handle key events for command history"""
        if obj == self.command_input and event.type() == QKeyEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                prev_cmd = self.shell_manager.get_history_prev()
                if prev_cmd is not None:
                    self.command_input.setText(prev_cmd)
                return True
            elif event.key() == Qt.Key.Key_Down:
                next_cmd = self.shell_manager.get_history_next()
                if next_cmd is not None:
                    self.command_input.setText(next_cmd)
                return True
        
        return super().eventFilter(obj, event)
    
    @Slot(str, bool)
    def _add_output(self, output: str, is_error: bool):
        """
        Add output to terminal
        
        Args:
            output: Output text
            is_error: True if error output
        """
        # Skip if output is just the echoed command we sent
        stripped = output.strip()
        if self.last_command and stripped == self.last_command:
            return
        
        # Skip shell prompt echoes (lines ending with $ or #)
        if stripped.endswith('$') or stripped.endswith('#'):
            if '@' in stripped or ':' in stripped:
                return
        
        color = QColor(244, 135, 113) if is_error else QColor(204, 204, 204)
        self._add_text(output, color)
        
        if '#' in output and 'root' in output.lower():
            self.is_root = True

    
    def _add_text(self, text: str, color: QColor):
        """
        Add colored text to terminal
        
        Args:
            text: Text to add
            color: Text color
        """
        cursor = self.terminal_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        format = cursor.charFormat()
        format.setForeground(color)
        cursor.setCharFormat(format)
        
        cursor.insertText(text)
        
        self.terminal_display.setTextCursor(cursor)
        self.terminal_display.ensureCursorVisible()
    
    def _add_prompt(self):
        """Add Termux-style command prompt"""
        device = self.current_device or "device"
        
        # Get path display (show ~ for home, basename for others)
        path_display = self._get_path_display()
        
        prompt_char = '#' if self.is_root else '$'
        
        user_part = f"shell@{device}"
        self._add_text(user_part, QColor(78, 201, 176))  # Cyan-green
        self._add_text(":", QColor(212, 212, 212))  # White
        self._add_text(path_display, QColor(86, 156, 214))  # Blue
        self._add_text(f" {prompt_char} ", QColor(106, 153, 85))  # Green

    
    def _get_path_display(self) -> str:
        """Get shortened path for display"""
        path = self.current_path
        
        if path == "/" or path == "/data/data":
            return "~"
        
        if len(path) > 20:
            parts = path.split('/')
            if len(parts) > 2:
                return "~/" + parts[-1]
        
        if path.startswith("/data/data/"):
            return "~" + path[10:]
        
        return path
    
    def _update_path_from_cd(self, command: str):
        """Update current path from cd command"""
        parts = command.split(maxsplit=1)
        if len(parts) < 2:
            self.current_path = "/data/data"  # cd with no args goes to home
            return
        
        new_path = parts[1].strip()
        
        if new_path == "~" or new_path == "":
            self.current_path = "/data/data"
        elif new_path == "/":
            self.current_path = "/"
        elif new_path.startswith("/"):
            self.current_path = new_path
        elif new_path == "..":
            if self.current_path != "/":
                self.current_path = "/".join(self.current_path.rstrip('/').split('/')[:-1]) or "/"
        else:
            if self.current_path == "/":
                self.current_path = "/" + new_path
            else:
                self.current_path = self.current_path.rstrip('/') + "/" + new_path
    
    @Slot()
    def _on_shell_started(self):
        """Handle shell started"""
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.command_input.setEnabled(True)
        
        self.current_path = "/"
        self.is_root = False
        
        self._add_text("=== Shell session started ===\n", QColor(106, 153, 85))
        self._add_prompt()
        self.command_input.setFocus()
    
    @Slot()
    def _on_shell_stopped(self):
        """Handle shell stopped"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.command_input.setEnabled(False)
        
        self._add_text("\n=== Shell session stopped ===\n", QColor(206, 145, 120))
    
    @Slot(str)
    def _on_shell_error(self, error: str):
        """Handle shell error"""
        self._add_text(f"\nError: {error}\n", QColor(244, 135, 113))
    
    @Slot()
    def _clear_terminal(self):
        """Clear terminal display"""
        self.terminal_display.clear()
        if self.shell_manager.is_active():
            self._add_prompt()
    
    @Slot()
    def _export_output(self):
        """Export terminal output to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Terminal Output", "terminal_output.txt", "Text Files (*.txt)"
        )
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.terminal_display.toPlainText())
            show_info(self, "ADB Manager", "Output exported successfully")
        except Exception as e:
            show_warning(self, "ADB Manager", f"Failed to export: {e}")
