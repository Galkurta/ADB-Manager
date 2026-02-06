"""
App List Widget - Manage installed applications

This widget provides a rich interface for managing installed applications
with icons, version info, and proper styling.
"""

import asyncio
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QComboBox, QLabel, QFileDialog, QMessageBox, QMenu,
    QProgressBar, QFrame, QSizePolicy, QAbstractItemView
)
from PySide6.QtCore import Qt, Slot, QSize
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QFont

from core.app_manager import AppManager, Package
from utils.ui_utils import show_warning, show_info

logger = logging.getLogger(__name__)


class AppItemWidget(QFrame):
    """Custom widget for displaying an app in the list"""
    
    def __init__(self, package: Package, parent=None):
        super().__init__(parent)
        self.package = package
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the item UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)
        
        # App icon (placeholder - will be a colored circle based on name)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(40, 40)
        self._set_placeholder_icon()
        layout.addWidget(self.icon_label)
        
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        self.name_label = QLabel(self.package.display_name)
        font = self.name_label.font()
        font.setPointSize(10)
        font.setBold(True)
        self.name_label.setFont(font)
        self.name_label.setStyleSheet("color: #ffffff;")
        info_layout.addWidget(self.name_label)
        
        version_text = f"v{self.package.version}" if self.package.version else ""
        details = self.package.package_name
        if version_text:
            details += f"  •  {version_text}"
        
        self.details_label = QLabel(details)
        details_font = self.details_label.font()
        details_font.setPointSize(8)
        self.details_label.setFont(details_font)
        self.details_label.setStyleSheet("color: #888888;")
        info_layout.addWidget(self.details_label)
        
        layout.addLayout(info_layout, 1)
        
        if self.package.is_system:
            badge = QLabel("System")
            badge.setStyleSheet("""
                QLabel {
                    background-color: #4a4a4a;
                    color: #aaaaaa;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-size: 9px;
                }
            """)
            layout.addWidget(badge)
        
        if not self.package.is_enabled:
            disabled_badge = QLabel("Disabled")
            disabled_badge.setStyleSheet("""
                QLabel {
                    background-color: #6b4423;
                    color: #ffaa66;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-size: 9px;
                }
            """)
            layout.addWidget(disabled_badge)
    
    def _set_placeholder_icon(self):
        """Create a colored placeholder icon based on package name"""
        hash_val = hash(self.package.package_name)
        hue = abs(hash_val) % 360
        
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        color = QColor.fromHsl(hue, 150, 100)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 36, 36)
        
        painter.setPen(Qt.white)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        
        letter = self.package.display_name[0].upper() if self.package.display_name else "?"
        painter.drawText(pixmap.rect(), Qt.AlignCenter, letter)
        
        painter.end()
        
        self.icon_label.setPixmap(pixmap)


class AppListWidget(QWidget):
    """Application list widget for managing apps"""
    
    def __init__(self, app_manager: AppManager):
        """
        Initialize App List Widget
        
        Args:
            app_manager: AppManager instance
        """
        super().__init__()
        self.app_manager = app_manager
        self.current_device = None
        self.packages = []
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(8, 8, 8, 0)
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Apps", "User Apps", "System Apps", "Enabled", "Disabled"])
        self.filter_combo.currentTextChanged.connect(self._filter_changed)
        filter_layout.addWidget(self.filter_combo)
        
        filter_layout.addStretch()
        
        self.count_label = QLabel("0 apps")
        self.count_label.setStyleSheet("color: #888888;")
        filter_layout.addWidget(self.count_label)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_list)
        filter_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(filter_layout)
        
        self.app_list = QListWidget()
        self.app_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.app_list.customContextMenuRequested.connect(self._show_context_menu)
        self.app_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.app_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.app_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3d3d3d;
                padding: 0px;
            }
            QListWidget::item:selected {
                background-color: #0d47a1;
            }
            QListWidget::item:hover:!selected {
                background-color: #383838;
            }
        """)
        layout.addWidget(self.app_list)
        
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(8, 0, 8, 8)
        
        self.install_btn = QPushButton("Install APK")
        self.install_btn.clicked.connect(self._install_apk)
        button_layout.addWidget(self.install_btn)
        
        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.clicked.connect(self._uninstall_app)
        button_layout.addWidget(self.uninstall_btn)
        
        self.launch_btn = QPushButton("Launch")
        self.launch_btn.clicked.connect(self._launch_app)
        button_layout.addWidget(self.launch_btn)
        
        self.clear_data_btn = QPushButton("Clear Data")
        self.clear_data_btn.clicked.connect(self._clear_data)
        button_layout.addWidget(self.clear_data_btn)
        
        layout.addLayout(button_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def _connect_signals(self):
        """Connect app manager signals"""
        self.app_manager.install_progress.connect(self._update_progress)
        self.app_manager.install_complete.connect(self._install_complete)
    
    def set_device(self, device: str):
        """
        Set current device
        
        Args:
            device: Device serial number
        """
        self.current_device = device
        asyncio.ensure_future(self._load_packages())
    
    async def _load_packages(self):
        """Load installed packages"""
        if not self.current_device:
            return
        
        try:
            self.app_list.clear()
            self.count_label.setText("Loading...")
            self.refresh_btn.setEnabled(False)
            
            filter_type = self._get_filter_type()
            self.packages = await self.app_manager.list_packages(
                self.current_device, filter_type
            )
            
            self.app_list.clear()
            for package in self.packages:
                item = QListWidgetItem(self.app_list)
                item.setData(Qt.UserRole, package)
                
                widget = AppItemWidget(package)
                item.setSizeHint(widget.sizeHint())
                
                self.app_list.addItem(item)
                self.app_list.setItemWidget(item, widget)
            
            self.count_label.setText(f"{len(self.packages)} apps")
            
        except Exception as e:
            logger.error(f"Failed to load packages: {e}")
            show_warning(self, "ADB Manager", f"Failed to load packages: {e}")
        finally:
            self.refresh_btn.setEnabled(True)
    
    def _get_filter_type(self) -> str:
        """Get filter type from combo box"""
        filter_text = self.filter_combo.currentText()
        filter_map = {
            "All Apps": "all",
            "User Apps": "user",
            "System Apps": "system",
            "Enabled": "enabled",
            "Disabled": "disabled"
        }
        return filter_map.get(filter_text, "all")
    
    @Slot()
    def _filter_changed(self):
        """Handle filter change"""
        asyncio.ensure_future(self._load_packages())
    
    @Slot()
    def _refresh_list(self):
        """Refresh package list"""
        asyncio.ensure_future(self._load_packages())
    
    @Slot()
    def _install_apk(self):
        """Install APK file"""
        if not self.current_device:
            show_warning(self, "ADB Manager", "No device selected")
            return
        
        apk_path, _ = QFileDialog.getOpenFileName(
            self, "Select APK File", "", "APK Files (*.apk)"
        )
        if not apk_path:
            return
        
        asyncio.ensure_future(
            self.app_manager.install_apk(self.current_device, Path(apk_path))
        )
    
    @Slot()
    def _uninstall_app(self):
        """Uninstall selected app"""
        if not self.current_device:
            return
        
        item = self.app_list.currentItem()
        if not item:
            show_warning(self, "ADB Manager", "No app selected")
            return
        
        package: Package = item.data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self, "Confirm Uninstall",
            f"Uninstall {package.display_name}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            asyncio.ensure_future(self._do_uninstall(package.package_name))
    
    async def _do_uninstall(self, package: str):
        """Perform uninstall operation"""
        success = await self.app_manager.uninstall_package(self.current_device, package)
        if success:
            await self._load_packages()
            show_info(self, "ADB Manager", "App uninstalled successfully")
        else:
            show_warning(self, "ADB Manager", "Failed to uninstall app")
    
    @Slot()
    def _launch_app(self):
        """Launch selected app"""
        if not self.current_device:
            return
        
        item = self.app_list.currentItem()
        if not item:
            return
        
        package: Package = item.data(Qt.UserRole)
        asyncio.ensure_future(
            self.app_manager.launch_app(self.current_device, package.package_name)
        )
    
    @Slot()
    def _clear_data(self):
        """Clear app data"""
        if not self.current_device:
            return
        
        item = self.app_list.currentItem()
        if not item:
            return
        
        package: Package = item.data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self, "Confirm Clear Data",
            f"Clear all data for {package.display_name}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            asyncio.ensure_future(self._do_clear_data(package.package_name))
    
    async def _do_clear_data(self, package: str):
        """Perform clear data operation"""
        success = await self.app_manager.clear_app_data(self.current_device, package)
        if success:
            show_info(self, "ADB Manager", "App data cleared")
        else:
            show_warning(self, "ADB Manager", "Failed to clear app data")
    
    @Slot(int, str)
    def _update_progress(self, progress: int, filename: str):
        """Update progress bar"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(progress)
    
    @Slot(bool, str)
    def _install_complete(self, success: bool, filename: str):
        """Handle install completion"""
        self.progress_bar.setVisible(False)
        if success:
            show_info(self, "ADB Manager", f"Installed {filename}")
            asyncio.ensure_future(self._load_packages())
        else:
            show_warning(self, "ADB Manager", f"Failed to install {filename}")
    
    @Slot()
    def _show_context_menu(self, position):
        """Show context menu"""
        item = self.app_list.itemAt(position)
        if not item:
            return
        
        package: Package = item.data(Qt.UserRole)
        
        menu = QMenu(self)
        
        launch_action = menu.addAction("Launch")
        uninstall_action = menu.addAction("Uninstall")
        clear_data_action = menu.addAction("Clear Data")
        clear_cache_action = menu.addAction("Clear Cache")
        
        menu.addSeparator()
        
        if package.is_enabled:
            disable_action = menu.addAction("Disable")
        else:
            enable_action = menu.addAction("Enable")
        
        action = menu.exec_(self.app_list.viewport().mapToGlobal(position))
        
        if action == launch_action:
            self._launch_app()
        elif action == uninstall_action:
            self._uninstall_app()
        elif action == clear_data_action:
            self._clear_data()
        elif action == clear_cache_action:
            asyncio.ensure_future(
                self.app_manager.clear_app_cache(self.current_device, package.package_name)
            )
        elif hasattr(action, 'text'):
            if action.text() == "Disable":
                asyncio.ensure_future(
                    self.app_manager.disable_package(self.current_device, package.package_name)
                )
            elif action.text() == "Enable":
                asyncio.ensure_future(
                    self.app_manager.enable_package(self.current_device, package.package_name)
                )
