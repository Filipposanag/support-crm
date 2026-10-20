# -*- coding: utf-8 -*-
"""
Splash screen with progress bar for application startup.
"""

from PySide6.QtWidgets import QSplashScreen, QProgressBar, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QLinearGradient
from pathlib import Path
import sys


class SplashScreen(QSplashScreen):
    """Modern splash screen with logo and progress bar."""
    
    def __init__(self):
        # Create a gradient background
        pixmap = QPixmap(600, 400)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create gradient background (grey)
        gradient = QLinearGradient(0, 0, 0, 400)
        gradient.setColorAt(0, QColor("#424242"))  # Darker grey
        gradient.setColorAt(1, QColor("#616161"))  # Lighter grey
        
        painter.fillRect(0, 0, 600, 400, gradient)
        
        # Add subtle overlay pattern
        overlay_color = QColor(255, 255, 255, 8)
        painter.fillRect(0, 0, 600, 200, overlay_color)
        
        painter.end()
        
        super().__init__(pixmap, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Load and display logo (larger and centered)
        self.logo_label = QLabel(self)
        logo_path = self._get_logo_path()
        if logo_path and logo_path.exists():
            logo_pixmap = QPixmap(str(logo_path))
            # Scale logo larger
            scaled_logo = logo_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(scaled_logo)
            self.logo_label.setGeometry(200, 60, 200, 200)
        else:
            # If no logo, hide the label
            self.logo_label.hide()
        
        # Create version label (below logo)
        from config import APP_VERSION
        self.version_label = QLabel(f"v{APP_VERSION}", self)
        self.version_label.setGeometry(50, 260, 500, 25)
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
                background: transparent;
            }
        """)
        
        # Create status label
        self.status_label = QLabel("Εκκίνηση εφαρμογής...", self)
        self.status_label.setGeometry(50, 295, 500, 25)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
            }
        """)
        
        # Create progress bar
        self.progress = QProgressBar(self)
        self.progress.setGeometry(100, 335, 400, 28)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid rgba(255, 255, 255, 0.5);
                border-radius: 15px;
                text-align: center;
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255, 255, 255, 0.9),
                    stop:1 rgba(255, 255, 255, 0.7));
                border-radius: 13px;
            }
        """)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
    
    def _get_logo_path(self):
        """Get the path to the logo file."""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_path = Path(sys._MEIPASS)
        else:
            # Running as script
            base_path = Path(__file__).parent.parent
        
        logo_path = base_path / 'Logo' / 'main_logo.png'
        return logo_path
    
    def update_progress(self, value: int, message: str = ""):
        """
        Update progress bar and status message.
        
        Args:
            value: Progress value (0-100)
            message: Status message to display
        """
        self.progress.setValue(value)
        if message:
            self.status_label.setText(message)
        self.repaint()
        QTimer.singleShot(10, lambda: None)  # Process events
