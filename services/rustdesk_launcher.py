# -*- coding: utf-8 -*-
"""
RustDesk Launcher Service
Handles launching RustDesk client for remote support sessions.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal, QTimer

logger = logging.getLogger(__name__)


class RustDeskLauncher(QObject):
    """
    Service for launching and monitoring RustDesk client connections.
    Uses process polling to detect when RustDesk actually closes,
    since RustDesk spawns child processes and the initial process
    exits immediately.
    """
    
    # Signals
    process_started = Signal(str)   # Emits client_id when RustDesk opens
    process_finished = Signal(str, int)  # Emits client_id and exit_code when RustDesk closes
    process_error = Signal(str, str)     # Emits client_id and error message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Active tracking: {client_id: tracking_info}
        self.active_processes = {}
        
        # RustDesk executable path
        self.rustdesk_path = self._find_rustdesk_executable()
        
        # Polling timer - checks every 2 seconds if RustDesk is still running
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(2000)
        self._poll_timer.timeout.connect(self._poll_rustdesk_running)
        
        logger.debug(f"RustDeskLauncher initialized. RustDesk path: {self.rustdesk_path}")
    
    def _find_rustdesk_executable(self) -> Optional[str]:
        """Find RustDesk executable on the system."""
        possible_paths = [
            Path.home() / "AppData" / "Local" / "RustDesk" / "rustdesk.exe",
            Path("C:/Program Files/RustDesk/rustdesk.exe"),
            Path("C:/Program Files (x86)/RustDesk/rustdesk.exe"),
            Path("rustdesk.exe"),
            Path("RustDesk/rustdesk.exe"),
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_file():
                logger.info(f"Found RustDesk at: {path}")
                return str(path.absolute())
        
        import shutil
        rustdesk_in_path = shutil.which("rustdesk")
        if rustdesk_in_path:
            logger.info(f"Found RustDesk in PATH: {rustdesk_in_path}")
            return rustdesk_in_path
        
        logger.warning("RustDesk executable not found")
        return None
    
    def is_rustdesk_available(self) -> bool:
        """Check if RustDesk is available on the system."""
        return self.rustdesk_path is not None
    
    def is_client_connected(self, client_id: str) -> bool:
        """Check if a connection to a client is currently active."""
        return client_id in self.active_processes
    
    def _is_rustdesk_running(self) -> bool:
        """Check if any rustdesk.exe process is currently running."""
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq rustdesk.exe', '/NH'],
                capture_output=True, text=True, timeout=3
            )
            return 'rustdesk.exe' in result.stdout
        except Exception:
            return False
    
    def _poll_rustdesk_running(self):
        """Poll to check if RustDesk is still running. Called every 2 seconds."""
        if not self.active_processes:
            self._poll_timer.stop()
            return
        
        running = self._is_rustdesk_running()
        logger.debug(f"RustDesk poll: running={running}, tracked clients={list(self.active_processes.keys())}")
        
        if not running:
            # RustDesk closed - notify all tracked clients
            logger.info("RustDesk process no longer running - ending sessions")
            self._poll_timer.stop()
            
            for client_id in list(self.active_processes.keys()):
                self.active_processes.pop(client_id, None)
                self.process_finished.emit(client_id, 0)
    
    def connect_to_client(
        self,
        rustdesk_id: str,
        password: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> bool:
        """
        Launch RustDesk and connect to a remote client.
        Starts polling to detect when RustDesk closes.
        """
        if not self.is_rustdesk_available():
            error_msg = "RustDesk is not installed or not found"
            logger.error(error_msg)
            self.process_error.emit(client_id or rustdesk_id, error_msg)
            return False
        
        if not rustdesk_id or not rustdesk_id.strip():
            error_msg = "RustDesk ID is required"
            logger.error(error_msg)
            self.process_error.emit(client_id or rustdesk_id, error_msg)
            return False
        
        tracking_id = client_id or rustdesk_id
        
        if self.is_client_connected(tracking_id):
            logger.warning(f"Already connected to client: {tracking_id}")
            return False
        
        try:
            # Build command arguments
            args = [self.rustdesk_path, "--connect", rustdesk_id]
            if password and password.strip():
                args.extend(["--password", password])
            
            logger.info(f"Launching RustDesk for client: {tracking_id}")
            
            # Launch RustDesk (non-blocking, fire-and-forget)
            # RustDesk spawns its own child processes so we don't track the PID
            subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Track this client
            self.active_processes[tracking_id] = {'rustdesk_id': rustdesk_id}
            
            # Emit started signal first
            self.process_started.emit(tracking_id)
            
            # Start polling after 3 seconds (give RustDesk time to open)
            QTimer.singleShot(3000, self._poll_timer.start)
            
            logger.info(f"RustDesk launched for client: {tracking_id}, polling will start in 3s")
            return True
            
        except Exception as e:
            error_msg = f"Error launching RustDesk: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.active_processes.pop(tracking_id, None)
            self.process_error.emit(tracking_id, error_msg)
            return False
    
    def disconnect_client(self, client_id: str) -> bool:
        """Terminate RustDesk connection to a client."""
        if client_id in self.active_processes:
            self.active_processes.pop(client_id, None)
        
        # Kill all rustdesk processes
        try:
            subprocess.run(
                ['taskkill', '/F', '/IM', 'rustdesk.exe'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            logger.info(f"RustDesk terminated for client: {client_id}")
            return True
        except Exception as e:
            logger.error(f"Error terminating RustDesk: {e}")
            return False
    
    def cleanup(self):
        """Cleanup all active processes."""
        self._poll_timer.stop()
        self.active_processes.clear()
        logger.info("RustDesk cleanup complete")
