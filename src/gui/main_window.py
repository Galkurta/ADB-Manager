"""
Main Window - Primary application window with tabbed interface

Provides the main UI for ADB Manager with device selection and module tabs.
"""

import asyncio
import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QComboBox, QLabel, QStatusBar,
    QMenuBar, QMenu, QMessageBox, QPushButton
)
from PySide6.QtCore import Qt, Slot, QSettings
from PySide6.QtGui import QAction, QIcon
from pathlib import Path

from utils.adb_wrapper import ADBWrapper
from utils.async_helper import safe_ensure_future
from core.device_manager import DeviceManager, Device
from gui.themes import ThemeManager, Theme

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, adb: ADBWrapper, device_manager: DeviceManager):
        """
        Initialize Main Window
        
        Args:
            adb: ADB wrapper instance
            device_manager: Device manager instance
        """
        super().__init__()
        self.adb = adb
        self.device_manager = device_manager
        self.current_device = None
        self.settings = QSettings('ADBManager', 'ADBManager')
        self.current_theme = Theme.DARK  # Default theme
        
        from gui.widgets import FileExplorerWidget, AppListWidget, LogcatViewerWidget, DeviceInfoWidget, MirrorViewerWidget, TerminalWidget
        from core.file_manager import FileManager
        from core.app_manager import AppManager
        from core.logcat_streamer import LogcatStreamer
        from core.shell_manager import ShellManager
        
        self.file_manager = FileManager(adb)
        self.app_manager = AppManager(adb)
        self.logcat_streamer = LogcatStreamer(adb)
        self.shell_manager = ShellManager(adb)
        
        self.file_explorer = FileExplorerWidget(self.file_manager)
        self.app_list = AppListWidget(self.app_manager)
        self.logcat_viewer = LogcatViewerWidget(self.logcat_streamer)
        self.device_info = DeviceInfoWidget(adb)
        self.mirror_viewer = MirrorViewerWidget()
        self.terminal = TerminalWidget(self.shell_manager)
        
        self._setup_ui()
        self._connect_signals()
        self._load_theme()
        
        logger.info("Main window initialized")
    
    def _setup_ui(self):
        """Setup user interface"""
        self.setWindowTitle("ADB Manager")
        self.setMinimumSize(1000, 700)
        
        icon_path = Path(__file__).parent.parent / "resources" / "icons" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Device:"))
        
        self.device_combo = QComboBox()
        self.device_combo.addItem("No device selected")
        # Use activated instead of currentTextChanged to catch user selections
        self.device_combo.activated.connect(lambda index: self._device_changed(self.device_combo.itemText(index)))
        device_layout.addWidget(self.device_combo)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setMaximumWidth(100)
        self.refresh_btn.clicked.connect(self._refresh_devices)
        self.refresh_btn.setToolTip("Refresh device list")
        device_layout.addWidget(self.refresh_btn)
        
        device_layout.addStretch()
        layout.addLayout(device_layout)
        
        self.tabs = QTabWidget()
        
        self.tabs.addTab(self.mirror_viewer, "Mirror")
        self.tabs.addTab(self.file_explorer, "Files")
        self.tabs.addTab(self.app_list, "Apps")
        self.tabs.addTab(self.logcat_viewer, "Logcat")
        self.tabs.addTab(self.terminal, "Terminal")
        self.tabs.addTab(self.device_info, "Info")
        
        layout.addWidget(self.tabs)
        
        self._setup_menu()
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _setup_menu(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        
        refresh_action = QAction("&Refresh Devices", self)
        refresh_action.triggered.connect(self._refresh_devices)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        tools_menu = menubar.addMenu("&Tools")
        
        wireless_action = QAction("&Wireless Connection", self)
        wireless_action.triggered.connect(self._show_wireless_dialog)
        tools_menu.addAction(wireless_action)
        
        tools_menu.addSeparator()
        
        settings_action = QAction("&Settings", self)
        settings_action.triggered.connect(self._show_settings)
        tools_menu.addAction(settings_action)
        
        view_menu = menubar.addMenu("&View")
        
        self.theme_action = QAction("Toggle &Theme (Dark/Light)", self)
        self.theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(self.theme_action)
        
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _connect_signals(self):
        """Connect device manager signals"""
        self.device_manager.device_connected.connect(self._on_device_connected)
        self.device_manager.device_disconnected.connect(self._on_device_disconnected)
        self.device_manager.device_unauthorized.connect(self._on_device_unauthorized)
        self.device_manager.devices_updated.connect(self._on_devices_updated)
    
    @Slot(str)
    def _device_changed(self, device_text: str):
        """Handle device selection change"""
        logger.info(f"Main Window: Device changed to: {device_text}")
        
        if device_text == "No device selected":
            self.current_device = None
            logger.info("Main Window: No device selected")
            return
        
        serial = device_text.split(" - ")[0]
        self.current_device = serial
        
        logger.info(f"Main Window: Setting device to {serial} for all widgets")
        
        self.file_explorer.set_device(serial)
        self.app_list.set_device(serial)
        self.logcat_viewer.set_device(serial)
        self.device_info.set_device(serial)
        self.mirror_viewer.set_device(serial)
        self.terminal.set_device(serial)
        
        self.status_bar.showMessage(f"Connected to {device_text}")
        logger.info(f"Selected device: {serial}")
    
    @Slot(str)
    def _on_device_connected(self, serial: str):
        """Handle device connected"""
        logger.info(f"Device connected: {serial}")
        self.status_bar.showMessage(f"Device connected: {serial}", 3000)
    
    @Slot(str)
    def _on_device_disconnected(self, serial: str):
        """Handle device disconnected"""
        logger.info(f"Device disconnected: {serial}")
        self.status_bar.showMessage(f"Device disconnected: {serial}", 3000)
        
        if self.current_device == serial:
            self.device_combo.setCurrentIndex(0)
    
    @Slot(str)
    def _on_device_unauthorized(self, serial: str):
        """Handle unauthorized device with actionable options"""
        logger.warning(f"Device unauthorized: {serial}")
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Device Unauthorized")
        msg.setText(f"Device {serial} is unauthorized.")
        msg.setInformativeText(
            "Please check your device for a USB debugging authorization popup.\n\n"
            "If no popup appears, try:\n"
            "• Restart ADB Server\n"
            "• Revoke USB authorizations in Developer Options and reconnect"
        )
        
        restart_btn = msg.addButton("Restart ADB", QMessageBox.ActionRole)
        retry_btn = msg.addButton("Retry", QMessageBox.ActionRole)
        msg.addButton(QMessageBox.Close)
        
        msg.exec()
        
        clicked = msg.clickedButton()
        if clicked == restart_btn:
            safe_ensure_future(self._restart_adb_and_refresh())
        elif clicked == retry_btn:
            safe_ensure_future(self._refresh_devices())
    
    async def _restart_adb_and_refresh(self):
        """Restart ADB server and refresh device list"""
        self.status_bar.showMessage("Restarting ADB server...")
        
        success = await self.adb.restart_server()
        
        if success:
            self.status_bar.showMessage("ADB server restarted. Scanning devices...", 2000)
            await self._refresh_devices()
        else:
            self.status_bar.showMessage("Failed to restart ADB server", 3000)
    
    async def _refresh_devices(self):
        """Refresh device list"""
        devices = await self.device_manager.scan_devices()
        self._on_devices_updated(devices)
    
    @Slot(list)
    def _on_devices_updated(self, devices: list):
        """Handle devices list update"""
        current_text = self.device_combo.currentText()
        
        self.device_combo.clear()
        self.device_combo.addItem("No device selected")
        
        for device in devices:
            display_text = f"{device.serial} - {device.model}"
            self.device_combo.addItem(display_text)
        
        index = self.device_combo.findText(current_text)
        if index >= 0:
            self.device_combo.setCurrentIndex(index)
        elif len(devices) > 0:
            self.device_combo.setCurrentIndex(1)  # Index 1 is first device (0 is "No device selected")
            # Manually trigger device change since setCurrentIndex doesn't emit activated signal
            self._device_changed(self.device_combo.itemText(1))
    
    @Slot()
    def _refresh_devices(self):
        """Manually refresh device list"""
        logger.info("Manually refreshing devices")
        self.status_bar.showMessage("Refreshing devices...", 2000)
    
    @Slot()
    def _show_wireless_dialog(self):
        """Show wireless connection dialog"""
        from gui.dialogs import WirelessDialog
        
        dialog = WirelessDialog(self.device_manager, self)
        dialog.exec_()
    
    
    @Slot()
    def _toggle_theme(self):
        """Toggle between dark and light themes"""
        self.current_theme = Theme.LIGHT if self.current_theme == Theme.DARK else Theme.DARK
        self._apply_theme()
        self.settings.setValue('theme', self.current_theme.value)
        logger.info(f"Theme changed to {self.current_theme.value}")
    
    def _load_theme(self):
        """Load theme from settings"""
        theme_str = self.settings.value('theme', Theme.DARK.value)
        try:
            self.current_theme = Theme(theme_str)
        except ValueError:
            self.current_theme = Theme.DARK
        self._apply_theme()
    
    def _apply_theme(self):
        """Apply current theme stylesheet"""
        stylesheet = ThemeManager.get_stylesheet(self.current_theme)
        self.setStyleSheet(stylesheet)
    
    @Slot()
    def _show_settings(self):
        """Show settings dialog"""
        from gui.dialogs import SettingsDialog
        
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self._load_theme()
    
    @Slot()
    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About ADB Manager",
            "<h3>ADB Manager v0.1.0</h3>"
            "<p>A modern GUI wrapper for Android Debug Bridge</p>"
            "<p>Built with Python and PySide6</p>"
        )
    
    def closeEvent(self, event):
        """Handle window close event - cleanup all async resources"""
        logger.info("Application closing - cleaning up resources")
        
        self.device_manager.stop_monitoring()
        
        # This prevents async cleanup from racing with event loop shutdown
        
        if self.logcat_streamer.is_streaming():
            self.logcat_streamer._streaming = False  # Signal stop
            if self.logcat_streamer._stream_task:
                self.logcat_streamer._stream_task.cancel()
        
        if self.shell_manager.is_active():
            self.shell_manager._active = False  # Signal stop
            if hasattr(self.shell_manager, '_read_task') and self.shell_manager._read_task:
                self.shell_manager._read_task.cancel()
            if hasattr(self.shell_manager, '_process') and self.shell_manager._process:
                try:
                    self.shell_manager._process.terminate()
                except Exception:
                    pass
        
        if hasattr(self.mirror_viewer, 'mirror_engine'):
            engine = self.mirror_viewer.mirror_engine
            if hasattr(engine, '_monitor_timer'):
                engine._monitor_timer.stop()
            if hasattr(engine, '_process') and engine._process:
                try:
                    engine._process.terminate()
                except Exception:
                    pass
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            for task in asyncio.all_tasks(loop):
                if not task.done():
                    task.cancel()
            loop.stop()
        except Exception:
            pass
        
        logger.info("Cleanup complete")
        event.accept()
        
        # Suppress Qt cleanup warnings at the Qt level
        from PySide6.QtCore import qInstallMessageHandler
        qInstallMessageHandler(lambda *args: None)
        
        import os
        os._exit(0)

