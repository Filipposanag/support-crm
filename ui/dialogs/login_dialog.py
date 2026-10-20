# -*- coding: utf-8 -*-
"""
Login dialog for user authentication.
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap

logger = logging.getLogger(__name__)


class LoginDialog(QDialog):
    """Dialog for user login."""
    
    login_successful = Signal(object)  # Emits User object on success
    
    def __init__(self, auth_service, parent=None):
        """
        Initialize the login dialog.
        
        Args:
            auth_service: AuthService instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.auth_service = auth_service
        self.user = None
        
        self.setWindowTitle("Σύνδεση - Support CRM")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setModal(True)
        
        # Set app icon
        try:
            from utils.resource_loader import app_icon
            self.setWindowIcon(app_icon())
        except:
            pass
        
        # Increased size to prevent logo cutoff when error appears
        self.setFixedSize(450, 520)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)
        
        # Logo section
        logo_layout = QVBoxLayout()
        logo_layout.setAlignment(Qt.AlignCenter)
        
        # Logo image
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        try:
            from utils.resource_loader import main_logo
            logo_pixmap = main_logo()
            if logo_pixmap and not logo_pixmap.isNull():
                # Scale logo to fit nicely
                scaled_logo = logo_pixmap.scaled(
                    200, 80,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.logo_label.setPixmap(scaled_logo)
            else:
                # Fallback to text if logo not found
                self.logo_label.setText("Support CRM")
                title_font = QFont()
                title_font.setPointSize(18)
                title_font.setBold(True)
                self.logo_label.setFont(title_font)
                self.logo_label.setStyleSheet("color: #2c3e50;")
        except Exception as e:
            logger.warning(f"Could not load logo: {e}")
            self.logo_label.setText("Support CRM")
            title_font = QFont()
            title_font.setPointSize(18)
            title_font.setBold(True)
            self.logo_label.setFont(title_font)
            self.logo_label.setStyleSheet("color: #2c3e50;")
        
        logo_layout.addWidget(self.logo_label)
        
        # Subtitle
        subtitle_label = QLabel("Σύνδεση Χρήστη")
        subtitle_font = QFont()
        subtitle_font.setPointSize(11)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #7f8c8d;")
        logo_layout.addWidget(subtitle_label)
        
        layout.addLayout(logo_layout)
        layout.addSpacing(5)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #ecf0f1;")
        layout.addWidget(separator)
        
        layout.addSpacing(10)
        
        # Form - Centered inputs
        form_container = QVBoxLayout()
        form_container.setSpacing(15)
        
        # Username field
        username_layout = QVBoxLayout()
        username_layout.setSpacing(5)
        username_label = QLabel("Χρήστης:")
        username_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        username_layout.addWidget(username_label)
        
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Εισάγετε όνομα χρήστη")
        self.username_edit.setMinimumHeight(40)
        self.username_edit.setAlignment(Qt.AlignCenter)  # Center text
        self.username_edit.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        self.username_edit.returnPressed.connect(self._focus_password)
        username_layout.addWidget(self.username_edit)
        form_container.addLayout(username_layout)
        
        # Password field
        password_layout = QVBoxLayout()
        password_layout.setSpacing(5)
        password_label = QLabel("Κωδικός:")
        password_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        password_layout.addWidget(password_label)
        
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Εισάγετε κωδικό")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMinimumHeight(40)
        self.password_edit.setAlignment(Qt.AlignCenter)  # Center text
        self.password_edit.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        self.password_edit.returnPressed.connect(self._on_login)
        password_layout.addWidget(self.password_edit)
        form_container.addLayout(password_layout)
        
        layout.addLayout(form_container)
        
        # Show password checkbox
        checkbox_layout = QHBoxLayout()
        checkbox_layout.addStretch()
        self.show_password_cb = QCheckBox("Εμφάνιση κωδικού")
        self.show_password_cb.toggled.connect(self._toggle_password_visibility)
        checkbox_layout.addWidget(self.show_password_cb)
        checkbox_layout.addStretch()
        layout.addLayout(checkbox_layout)
        
        layout.addSpacing(5)
        
        # Error message label (fixed height to prevent layout shift)
        self.error_label = QLabel("")
        self.error_label.setMinimumHeight(50)  # Reserve space for error
        self.error_label.setMaximumHeight(50)
        self.error_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                background-color: #fdf2f2;
                border: 1px solid #f5c6cb;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        self.error_label.setWordWrap(True)
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        layout.addWidget(self.error_label)
        
        layout.addStretch()
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.login_button = QPushButton("Σύνδεση")
        self.login_button.setMinimumHeight(40)
        self.login_button.setMinimumWidth(120)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.login_button.clicked.connect(self._on_login)
        buttons_layout.addWidget(self.login_button)
        
        self.cancel_button = QPushButton("Έξοδος")
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        # Focus on username
        self.username_edit.setFocus()
    
    def _focus_password(self):
        """Move focus to password field."""
        self.password_edit.setFocus()
    
    def _toggle_password_visibility(self, checked: bool):
        """Toggle password visibility."""
        if checked:
            self.password_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.password_edit.setEchoMode(QLineEdit.Password)
    
    def _show_error(self, message: str):
        """Show error message."""
        self.error_label.setText(message)
        self.error_label.show()
    
    def _hide_error(self):
        """Hide error message."""
        self.error_label.hide()
    
    def _on_login(self):
        """Handle login button click."""
        self._hide_error()
        
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        
        # Validation
        if not username:
            self._show_error("Παρακαλώ εισάγετε όνομα χρήστη")
            self.username_edit.setFocus()
            return
        
        if not password:
            self._show_error("Παρακαλώ εισάγετε κωδικό")
            self.password_edit.setFocus()
            return
        
        # Disable button during login
        self.login_button.setEnabled(False)
        self.login_button.setText("Σύνδεση...")
        
        try:
            # Attempt login
            success, message, user = self.auth_service.login(username, password)
            
            if success:
                self.user = user
                self.login_successful.emit(user)
                logger.info(f"Login successful for user: {username}")
                self.accept()
            else:
                self._show_error(message)
                self.password_edit.clear()
                self.password_edit.setFocus()
                logger.warning(f"Login failed for user: {username} - {message}")
        except Exception as e:
            self._show_error(f"Σφάλμα σύνδεσης: {str(e)}")
            logger.error(f"Login error: {e}")
        finally:
            self.login_button.setEnabled(True)
            self.login_button.setText("Σύνδεση")
    
    def get_user(self):
        """Get the logged-in user."""
        return self.user
