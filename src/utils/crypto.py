"""
Credential encryption utilities

This module provides secure storage for wireless ADB credentials.
"""

import logging
from pathlib import Path
from cryptography.fernet import Fernet
from PySide6.QtCore import QSettings

logger = logging.getLogger(__name__)


class CredentialManager:
    """Manages encrypted credential storage"""
    
    def __init__(self):
        """Initialize credential manager"""
        self.settings = QSettings("ADB Manager", "Credentials")
        self._ensure_key()
        logger.info("Credential Manager initialized")
    
    def _ensure_key(self):
        """Ensure encryption key exists"""
        key = self.settings.value("encryption_key")
        if not key:
            key = Fernet.generate_key().decode()
            self.settings.setValue("encryption_key", key)
        
        self.cipher = Fernet(key.encode())
    
    def store_wireless_credential(self, ip: str, port: int, pairing_code: str = ""):
        """
        Store wireless ADB credentials
        
        Args:
            ip: Device IP address
            port: ADB port
            pairing_code: Optional pairing code
        """
        try:
            data = f"{ip}:{port}:{pairing_code}"
            encrypted = self.cipher.encrypt(data.encode())
            
            self.settings.setValue(f"wireless/{ip}", encrypted.decode())
            logger.info(f"Stored credentials for {ip}")
            
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
    
    def retrieve_wireless_credential(self, ip: str) -> tuple:
        """
        Retrieve wireless ADB credentials
        
        Args:
            ip: Device IP address
        
        Returns:
            Tuple of (ip, port, pairing_code)
        """
        try:
            encrypted = self.settings.value(f"wireless/{ip}")
            if not encrypted:
                return None, None, None
            
            decrypted = self.cipher.decrypt(encrypted.encode()).decode()
            parts = decrypted.split(':')
            
            ip = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 5555
            pairing_code = parts[2] if len(parts) > 2 else ""
            
            return ip, port, pairing_code
            
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            return None, None, None
    
    def delete_wireless_credential(self, ip: str):
        """
        Delete wireless ADB credentials
        
        Args:
            ip: Device IP address
        """
        try:
            self.settings.remove(f"wireless/{ip}")
            logger.info(f"Deleted credentials for {ip}")
        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}")
