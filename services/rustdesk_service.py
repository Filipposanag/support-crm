# -*- coding: utf-8 -*-
"""
RustDesk Service for Support CRM.
Handles RustDesk remote connection integration.
"""

import subprocess
import logging
import os
from typing import Optional, Dict, Any
from pathlib import Path


logger = logging.getLogger(__name__)


class RustDeskService:
    """Service for managing RustDesk remote connections."""
    
    def __init__(self, rustdesk_path: Optional[str] = None):
        """
        Initialize RustDesk service.
        
        Args:
            rustdesk_path: Path to RustDesk executable. If None, searches in common locations.
        """
        self.rustdesk_path = rustdesk_path or self._find_rustdesk_executable()
        self.server_host = ''
        self.server_port = 21116
        self.api_key = ''
        
    def _find_rustdesk_executable(self) -> Optional[str]:
        """
        Find RustDesk executable in common installation locations.
        
        Returns:
            Path to RustDesk executable or None if not found.
        """
        # Common installation paths on Windows
        common_paths = [
            r"C:\Program Files\RustDesk\rustdesk.exe",
            r"C:\Program Files (x86)\RustDesk\rustdesk.exe",
            os.path.expanduser(r"~\AppData\Local\RustDesk\rustdesk.exe"),
            r".\rustdesk.exe",  # Current directory
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                logger.info(f"Found RustDesk executable at: {path}")
                return path
        
        logger.warning("RustDesk executable not found in common locations")
        return None
    
    def configure_server(self, host: str, port: int = 21116, api_key: str = ''):
        """
        Configure RustDesk server settings.
        
        Args:
            host: RustDesk server hostname or IP
            port: RustDesk server port (default: 21116)
            api_key: API key for authentication (if required)
        """
        self.server_host = host
        self.server_port = port
        self.api_key = api_key
        logger.info(f"RustDesk server configured: {host}:{port}")
    
    def is_available(self) -> bool:
        """
        Check if RustDesk is available and configured.
        
        Returns:
            True if RustDesk executable is found, False otherwise.
        """
        return self.rustdesk_path is not None and os.path.exists(self.rustdesk_path)
    
    def connect_to_client(self, rustdesk_id: str, password: Optional[str] = None) -> bool:
        """
        Launch RustDesk and connect to a client.
        
        Args:
            rustdesk_id: RustDesk client ID to connect to
            password: Optional password for connection
            
        Returns:
            True if connection launched successfully, False otherwise.
        """
        if not self.is_available():
            logger.error("RustDesk is not available")
            return False
        
        if not rustdesk_id:
            logger.error("RustDesk ID is required")
            return False
        
        try:
            # Build command
            cmd = [self.rustdesk_path, "--connect", rustdesk_id]
            
            # Add password if provided
            if password:
                cmd.extend(["--password", password])
            
            # Add custom server if configured
            if self.server_host:
                cmd.extend(["--server", f"{self.server_host}:{self.server_port}"])
            
            logger.info(f"Launching RustDesk connection to: {rustdesk_id}")
            logger.debug(f"Command: {' '.join(cmd[:4])}...")  # Don't log password
            
            # Launch RustDesk (non-blocking)
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            logger.info(f"RustDesk connection launched successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to launch RustDesk connection: {e}")
            return False
    
    def get_connection_url(self, rustdesk_id: str) -> str:
        """
        Get RustDesk connection URL (for manual connection).
        
        Args:
            rustdesk_id: RustDesk client ID
            
        Returns:
            Connection URL string
        """
        if self.server_host:
            return f"rustdesk://{self.server_host}:{self.server_port}/{rustdesk_id}"
        return f"rustdesk://{rustdesk_id}"
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test RustDesk availability and configuration.
        
        Returns:
            Dictionary with test results:
            - available: bool - RustDesk executable found
            - path: str - Path to executable
            - server_configured: bool - Custom server configured
            - server: str - Server address
        """
        result = {
            'available': self.is_available(),
            'path': self.rustdesk_path or 'Not found',
            'server_configured': bool(self.server_host),
            'server': f"{self.server_host}:{self.server_port}" if self.server_host else 'Default (public)',
        }
        
        logger.info(f"RustDesk test: {result}")
        return result
    
    def open_rustdesk_settings(self) -> bool:
        """
        Open RustDesk settings window.
        
        Returns:
            True if launched successfully, False otherwise.
        """
        if not self.is_available():
            logger.error("RustDesk is not available")
            return False
        
        try:
            # Launch RustDesk without connection (opens main window)
            subprocess.Popen(
                [self.rustdesk_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            logger.info("RustDesk settings window launched")
            return True
            
        except Exception as e:
            logger.error(f"Failed to open RustDesk settings: {e}")
            return False
    
    def disconnect_all(self) -> bool:
        """
        Close all RustDesk connections by killing RustDesk processes.
        
        Returns:
            True if processes were killed successfully, False otherwise.
        """
        try:
            if os.name == 'nt':  # Windows
                # Kill all rustdesk.exe processes
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'rustdesk.exe'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
                logger.info("RustDesk processes terminated")
                return True
            else:  # Linux/Mac
                subprocess.run(
                    ['pkill', '-9', 'rustdesk'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
                logger.info("RustDesk processes terminated")
                return True
                
        except Exception as e:
            logger.error(f"Failed to terminate RustDesk processes: {e}")
            return False
    
    def get_client_id_from_clipboard(self) -> Optional[str]:
        """
        Get RustDesk ID from clipboard (if user copied it).
        
        Returns:
            RustDesk ID if valid format found in clipboard, None otherwise.
        """
        try:
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            text = clipboard.text().strip()
            
            # Basic validation: RustDesk IDs are typically 9-10 digits
            if text.isdigit() and 9 <= len(text) <= 10:
                logger.info(f"Valid RustDesk ID found in clipboard")
                return text
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to read clipboard: {e}")
            return None
