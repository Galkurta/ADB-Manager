"""
File Explorer Widget - Browse and manage device files

This widget provides a file browser interface for device file systems.
"""

import asyncio
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QLabel, QProgressBar, QFileDialog,
    QMessageBox, QMenu
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon

from core.file_manager import FileManager, FileInfo
from utils.ui_utils import show_warning

logger = logging.getLogger(__name__)


class FileExplorerWidget(QWidget):
    """File explorer widget for browsing device files"""
    
    def __init__(self, file_manager: FileManager):
        """
        Initialize File Explorer Widget
        
        Args:
            file_manager: FileManager instance
        """
        super().__init__()
        self.file_manager = file_manager
        self.current_device = None
        self.current_path = "/sdcard"
        self._is_refreshing = False
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        path_layout = QHBoxLayout()
        
        self.up_btn = QPushButton("Up")
        self.up_btn.setMaximumWidth(70)
        self.up_btn.clicked.connect(self._navigate_up)
        self.up_btn.setToolTip("Go to parent directory")
        path_layout.addWidget(self.up_btn)
        
        path_layout.addWidget(QLabel("Path:"))
        self.path_edit = QLineEdit(self.current_path)
        self.path_edit.returnPressed.connect(self._navigate_to_path)
        path_layout.addWidget(self.path_edit)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setMaximumWidth(80)
        self.refresh_btn.clicked.connect(self._refresh_directory)
        self.refresh_btn.setToolTip("Refresh directory")
        path_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(path_layout)
        
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["Name", "Size", "Permissions", "Modified"])
        self.file_tree.setColumnWidth(0, 300)  # Name column wider
        self.file_tree.setColumnWidth(1, 100)  # Size column
        self.file_tree.setColumnWidth(2, 120)  # Permissions column
        self.file_tree.setColumnWidth(3, 150)  # Modified column
        self.file_tree.setAlternatingRowColors(True)
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self._show_context_menu)
        self.file_tree.itemDoubleClicked.connect(self._item_double_clicked)
        layout.addWidget(self.file_tree)
        
        button_layout = QHBoxLayout()
        
        self.push_btn = QPushButton("Push File")
        self.push_btn.clicked.connect(self._push_file)
        button_layout.addWidget(self.push_btn)
        
        self.pull_btn = QPushButton("Pull File")
        self.pull_btn.clicked.connect(self._pull_file)
        button_layout.addWidget(self.pull_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_file)
        button_layout.addWidget(self.delete_btn)
        
        self.mkdir_btn = QPushButton("New Folder")
        self.mkdir_btn.clicked.connect(self._create_directory)
        button_layout.addWidget(self.mkdir_btn)
        
        layout.addLayout(button_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def _connect_signals(self):
        """Connect file manager signals"""
        self.file_manager.transfer_progress.connect(self._update_progress)
        self.file_manager.transfer_complete.connect(self._transfer_complete)
    
    def set_device(self, device: str):
        """
        Set current device
        
        Args:
            device: Device serial number
        """
        logger.info(f"File Explorer: Setting device to {device}")
        self.current_device = device
        asyncio.ensure_future(self._load_directory(self.current_path))
    
    async def _load_directory(self, path: str):
        """Load directory contents"""
        logger.debug(f"File Explorer: Loading directory {path}, device={self.current_device}")
        
        if not self.current_device:
            logger.warning("File Explorer: No device selected, cannot load directory")
            return
        
        if self._is_refreshing:
            logger.debug("File Explorer: Already refreshing, skipping")
            return
        
        self._is_refreshing = True
        
        try:
            self.file_tree.clear()
            files = await self.file_manager.list_directory(self.current_device, path)
            
            logger.debug(f"File Explorer: Received {len(files)} files")
            
            directories = [f for f in files if f.is_directory]
            regular_files = [f for f in files if not f.is_directory]
            
            for file_info in directories + regular_files:
                name = file_info.name
                if file_info.is_directory:
                    name = f"📁 {name}"
                else:
                    name = f"📄 {name}"
                
                modified = file_info.modified_time if hasattr(file_info, 'modified_time') else ""
                
                item = QTreeWidgetItem([
                    name,
                    file_info.display_size if not file_info.is_directory else "<DIR>",
                    file_info.permissions,
                    modified
                ])
                item.setData(0, Qt.UserRole, file_info)
                
                if file_info.is_directory:
                    font = item.font(0)
                    font.setBold(True)
                    item.setFont(0, font)
                
                self.file_tree.addTopLevelItem(item)
            
            self.current_path = path
            self.path_edit.setText(path)
            
        except Exception as e:
            logger.error(f"Failed to load directory: {e}")
            show_warning(self, "ADB Manager", f"Failed to load directory: {e}")
        finally:
            self._is_refreshing = False

    
    @Slot()
    def _navigate_to_path(self):
        """Navigate to path from path edit"""
        path = self.path_edit.text()
        asyncio.ensure_future(self._load_directory(path))
    
    @Slot()
    def _navigate_up(self):
        """Navigate to parent directory"""
        if self.current_path == "/":
            return
        
        parent_path = "/".join(self.current_path.rstrip("/").split("/")[:-1])
        if not parent_path:
            parent_path = "/"
        
        asyncio.ensure_future(self._load_directory(parent_path))
    
    @Slot()
    def _refresh_directory(self):
        """Refresh current directory"""
        asyncio.ensure_future(self._load_directory(self.current_path))
    
    @Slot(QTreeWidgetItem, int)
    def _item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item double click"""
        file_info: FileInfo = item.data(0, Qt.UserRole)
        if file_info.is_directory:
            asyncio.ensure_future(self._load_directory(file_info.path))
    
    @Slot()
    def _push_file(self):
        """Push file to device"""
        if not self.current_device:
            show_warning(self, "ADB Manager", "No device selected")
            return
        
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Push")
        if not file_path:
            return
        
        local_path = Path(file_path)
        remote_path = f"{self.current_path}/{local_path.name}"
        
        asyncio.ensure_future(
            self.file_manager.push_file(self.current_device, local_path, remote_path)
        )
    
    @Slot()
    def _pull_file(self):
        """Pull file from device"""
        if not self.current_device:
            show_warning(self, "ADB Manager", "No device selected")
            return
        
        item = self.file_tree.currentItem()
        if not item:
            show_warning(self, "ADB Manager", "No file selected")
            return
        
        file_info: FileInfo = item.data(0, Qt.UserRole)
        if file_info.is_directory:
            show_warning(self, "ADB Manager", "Cannot pull directories")
            return
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save File As", file_info.name
        )
        if not save_path:
            return
        
        asyncio.ensure_future(
            self.file_manager.pull_file(
                self.current_device, file_info.path, Path(save_path)
            )
        )
    
    @Slot()
    def _delete_file(self):
        """Delete selected file"""
        if not self.current_device:
            return
        
        item = self.file_tree.currentItem()
        if not item:
            return
        
        file_info: FileInfo = item.data(0, Qt.UserRole)
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {file_info.name}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            asyncio.ensure_future(self._do_delete(file_info.path))
    
    async def _do_delete(self, path: str):
        """Perform delete operation"""
        success = await self.file_manager.delete_file(self.current_device, path)
        if success:
            await self._load_directory(self.current_path)
        else:
            show_warning(self, "ADB Manager", "Failed to delete file")
    
    @Slot()
    def _create_directory(self):
        """Create new directory"""
        from PySide6.QtWidgets import QInputDialog
        
        if not self.current_device:
            return
        
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name:
            path = f"{self.current_path}/{name}"
            asyncio.ensure_future(self._do_mkdir(path))
    
    async def _do_mkdir(self, path: str):
        """Perform mkdir operation"""
        success = await self.file_manager.create_directory(self.current_device, path)
        if success:
            await self._load_directory(self.current_path)
        else:
            show_warning(self, "ADB Manager", "Failed to create directory")
    
    @Slot(int, int, str)
    def _update_progress(self, current: int, total: int, filename: str):
        """Update progress bar"""
        self.progress_bar.setVisible(True)
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
    
    @Slot(bool, str)
    def _transfer_complete(self, success: bool, filename: str):
        """Handle transfer completion"""
        self.progress_bar.setVisible(False)
        if success:
            asyncio.ensure_future(self._load_directory(self.current_path))
    
    @Slot()
    def _show_context_menu(self, position):
        """Show context menu"""
        item = self.file_tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        pull_action = menu.addAction("Pull")
        delete_action = menu.addAction("Delete")
        
        action = menu.exec_(self.file_tree.viewport().mapToGlobal(position))
        
        if action == pull_action:
            self._pull_file()
        elif action == delete_action:
            self._delete_file()
