"""
Main application entry point

Launches the ADB Manager GUI application.
"""

import sys
import asyncio
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import qasync

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import setup_logger
from utils.adb_wrapper import ADBWrapper
from core.device_manager import DeviceManager
from gui.main_window import MainWindow

# Set up logging
logger = setup_logger("adb_manager", level=10)  # DEBUG level


def main():
    """Main application entry point"""
    logger.info("Starting ADB Manager...")
    
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    
    # Version Control
    __version__ = "0.1.0"
    
    app.setApplicationName("ADB Manager")
    app.setOrganizationName("ADB Manager")
    app.setApplicationVersion(__version__)
    
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    adb = ADBWrapper()
    device_manager = DeviceManager(adb)
    window = MainWindow(adb, device_manager)
    window.show()
    
    logger.info("Starting device monitoring...")
    device_manager.start_monitoring()
    logger.info("Application started successfully")
    with loop:
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.stop()
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending and loop.is_running():
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            import warnings
            warnings.filterwarnings("ignore", message=".*unclosed transport.*")



if __name__ == "__main__":
    main()

