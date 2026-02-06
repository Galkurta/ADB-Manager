import logging
import requests
import webbrowser
from packaging import version as semantic_version
from PySide6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

REPO_OWNER = "Galkurta"
REPO_NAME = "ADB-Manager"
API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

class UpdateChecker:
    @staticmethod
    def check_for_updates(current_version, parent_widget=None, silent=False):
        """
        Checks GitHub for updates.
        Args:
            current_version (str): The current app version.
            parent_widget (QWidget): Parent for message boxes.
            silent (bool): If True, suppresses 'Up to date' message.
        """
        try:
            logger.info(f"Checking for updates (Current: {current_version})...")
            # timeout=3 to minimize UI freeze
            response = requests.get(API_URL, timeout=3)
            response.raise_for_status()
            
            data = response.json()
            latest_tag = data.get("tag_name", "").lstrip("v")
            html_url = data.get("html_url", "")
            
            if not latest_tag:
                logger.warning("Could not parse version tag from GitHub response")
                if not silent and parent_widget:
                    QMessageBox.warning(parent_widget, "Update Error", "Could not retrieve version info from GitHub.")
                return

            if semantic_version.parse(latest_tag) > semantic_version.parse(current_version):
                logger.info(f"Update available: {latest_tag}")
                if parent_widget:
                    reply = QMessageBox.question(
                        parent_widget,
                        "Update Available",
                        f"<p style='text-align: center;'>A new version is available!</p>"
                        f"<p style='text-align: center;'>"
                        f"Current: <b>v{current_version}</b><br>"
                        f"Latest: <b>v{latest_tag}</b></p>"
                        f"<p style='text-align: center;'>Download now?</p>",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        webbrowser.open(html_url)
            else:
                logger.info("App is up to date.")
                if not silent and parent_widget:
                    QMessageBox.information(
                        parent_widget, 
                        "Up to Date", 
                        f"<p style='text-align: center;'>You are using the latest version<br><b>v{current_version}</b></p>"
                    )

        except Exception as e:
            logger.error(f"Update check failed: {e}")
            if not silent and parent_widget:
                # Don't show confusing errors if it's just a connection issue, unless specific
                QMessageBox.warning(parent_widget, "Update Error", f"Failed to check for updates.\n{e}")
