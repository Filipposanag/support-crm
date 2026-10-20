# -*- coding: utf-8 -*-
"""
Update Available Dialog - Custom styled dialog for update notifications.
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

logger = logging.getLogger(__name__)


class UpdateAvailableDialog(QDialog):
    """Custom dialog for displaying update notifications."""
    
    def __init__(self, current_version: str, new_version: str, changelog: str, mandatory: bool = False, parent=None):
        """
        Initialize the update available dialog.
        
        Args:
            current_version: Current application version
            new_version: New available version
            changelog: Release notes/changelog
            mandatory: Whether update is mandatory
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.current_version = current_version
        self.new_version = new_version
        self.changelog = changelog
        self.mandatory = mandatory
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Βρέθηκε νέα έκδοση")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Set white background (prevent dark mode override)
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QColor("#ffffff"))
        self.setPalette(pal)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        # Icon
        icon_label = QLabel("🔄")
        icon_label.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel("Διαθέσιμη Νέα Έκδοση")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2196F3;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Version info
        version_text = f"Τρέχουσα έκδοση: <b>{self.current_version}</b><br>"
        version_text += f"Νέα έκδοση: <b style='color: #4CAF50;'>{self.new_version}</b>"
        
        version_label = QLabel(version_text)
        version_label.setTextFormat(Qt.RichText)
        version_label.setStyleSheet("font-size: 13px; padding: 8px 0px;")
        layout.addWidget(version_label)
        
        # Mandatory warning (if applicable)
        if self.mandatory:
            warning_label = QLabel("⚠️ Αυτή η ενημέρωση είναι υποχρεωτική")
            warning_label.setStyleSheet(
                "background-color: #FFF3CD; "
                "color: #856404; "
                "padding: 12px; "
                "border-radius: 4px; "
                "border: 1px solid #FFE69C; "
                "font-weight: 500;"
            )
            layout.addWidget(warning_label)
        
        # Changelog section
        if self.changelog:
            changelog_label = QLabel("Σημειώσεις Έκδοσης:")
            changelog_label.setStyleSheet("font-weight: 500; font-size: 13px; margin-top: 8px;")
            layout.addWidget(changelog_label)
            
            changelog_text = QTextEdit()
            changelog_text.setPlainText(self.changelog)
            changelog_text.setReadOnly(True)
            changelog_text.setMaximumHeight(200)
            changelog_text.setStyleSheet(
                "QTextEdit { "
                "background-color: #F5F5F5; "
                "border: 1px solid #E0E0E0; "
                "border-radius: 4px; "
                "padding: 8px; "
                "font-size: 12px; "
                "color: #212121; "
                "}"
            )
            layout.addWidget(changelog_text)
        
        # Spacer
        layout.addStretch()
        
        # Separator line
        separator = QLabel()
        separator.setStyleSheet("background-color: #E0E0E0; max-height: 1px;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 12, 0, 0)
        buttons_layout.setSpacing(12)
        buttons_layout.setAlignment(Qt.AlignRight)
        
        # Cancel button (only if not mandatory)
        if not self.mandatory:
            cancel_button = QPushButton("Άκυρο")
            cancel_button.setObjectName("secondaryButton")
            cancel_button.setMinimumWidth(140)
            cancel_button.setFixedHeight(36)
            cancel_button.clicked.connect(self.reject)
            buttons_layout.addWidget(cancel_button)
        
        # Update button
        update_button = QPushButton("Λήψη Ενημέρωσης")
        update_button.setObjectName("primaryButton")
        update_button.setMinimumWidth(140)
        update_button.setFixedHeight(36)
        update_button.setDefault(True)
        update_button.setAutoDefault(True)
        update_button.clicked.connect(self.accept)
        buttons_layout.addWidget(update_button)
        
        layout.addLayout(buttons_layout)
        
        logger.debug(f"Update dialog created: {self.current_version} -> {self.new_version}")
