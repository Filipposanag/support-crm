# -*- coding: utf-8 -*-
"""
License Activation Dialog - Modal dialog for license activation on startup.
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from services.license_service import LicenseService
from services.settings_service import SettingsService
from ui.i18n import get_translation_manager

logger = logging.getLogger(__name__)


class LicenseActivationDialog(QDialog):
    """
    Modal dialog for license activation.
    Shown on startup if no active license is found.
    """
    
    def __init__(self, settings_service: SettingsService, parent=None):
        """
        Initialize license activation dialog.
        
        Args:
            settings_service: Settings service instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.settings_service = settings_service
        self.tr = get_translation_manager()
        
        self.setWindowTitle(self.tr.get('license_activation_title'))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        # Prevent closing with X button
        self.setWindowFlags(
            Qt.Dialog | 
            Qt.WindowTitleHint | 
            Qt.CustomizeWindowHint
        )
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel(self.tr.get('license_activation_required'))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Description
        desc = QLabel(self.tr.get('license_activation_desc'))
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # License key input
        key_label = QLabel(self.tr.get('license_key_label'))
        key_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(key_label)
        
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText(self.tr.get('license_key_placeholder'))
        self.key_edit.setMinimumHeight(35)
        self.key_edit.setStyleSheet("padding: 8px; font-size: 13px;")
        self.key_edit.returnPressed.connect(self._on_activate)
        layout.addWidget(self.key_edit)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_exit = QPushButton(self.tr.get('license_btn_exit'))
        self.btn_exit.setMinimumHeight(40)
        self.btn_exit.setStyleSheet(
            "background-color: #757575; color: white; "
            "font-weight: bold; padding: 10px; font-size: 13px;"
        )
        self.btn_exit.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_exit)
        
        self.btn_activate = QPushButton(self.tr.get('license_btn_activate'))
        self.btn_activate.setMinimumHeight(40)
        self.btn_activate.setStyleSheet(
            "background-color: #4CAF50; color: white; "
            "font-weight: bold; padding: 10px; font-size: 13px;"
        )
        self.btn_activate.clicked.connect(self._on_activate)
        self.btn_activate.setDefault(True)
        btn_layout.addWidget(self.btn_activate)
        
        layout.addLayout(btn_layout)
        
        # Focus on input
        self.key_edit.setFocus()
    
    def _on_activate(self):
        """Handle activation button click."""
        key = self.key_edit.text().strip()
        
        if not key:
            QMessageBox.warning(
                self,
                self.tr.get('error_title'),
                self.tr.get('license_empty_key')
            )
            self.key_edit.setFocus()
            return
        
        # Disable button during validation
        self.btn_activate.setEnabled(False)
        self.btn_activate.setText(self.tr.get('license_btn_activating'))
        
        try:
            # Try online validation first
            from services.license_validator import check_license_status
            import config
            
            validation_result = check_license_status(
                license_key=key,
                validation_url=config.LICENSE_VALIDATION_CONFIG['validation_url'],
                timeout=config.LICENSE_VALIDATION_CONFIG['timeout']
            )
            
            if validation_result['online']:
                # Online validation completed (server responded)
                if validation_result['valid']:
                    # Valid license - use dates from server
                    owner = validation_result['owner_name']
                    start_date = validation_result['start_date']
                    end_date = validation_result['end_date']
                    logger.info(f"Online license validation successful: {owner}")
                else:
                    # Invalid or expired license
                    QMessageBox.critical(
                        self,
                        self.tr.get('license_problem_title'),
                        self.tr.get('license_problem_message')
                    )
                    logger.warning(f"Invalid license key attempted: {key}")
                    self.btn_activate.setEnabled(True)
                    self.btn_activate.setText(self.tr.get('license_btn_activate'))
                    self.key_edit.setFocus()
                    self.key_edit.selectAll()
                    return
            else:
                # Online validation failed - REQUIRE internet connection
                logger.warning("Online validation failed - internet required")
                
                QMessageBox.critical(
                    self,
                    self.tr.get('license_problem_title'),
                    self.tr.get('license_problem_message')
                )
                
                logger.warning(f"License validation failed - no connection: {key}")
                self.btn_activate.setEnabled(True)
                self.btn_activate.setText(self.tr.get('license_btn_activate'))
                self.key_edit.setFocus()
                self.key_edit.selectAll()
                return
            
            # Save license to database
            if self.settings_service.set_license(
                license_key=key,
                owner=owner,
                start_date=start_date,
                end_date=end_date,
                status='active'
            ):
                # Format dates for display
                from datetime import datetime
                if isinstance(start_date, str):
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                else:
                    start_date_obj = start_date
                
                if isinstance(end_date, str):
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                else:
                    end_date_obj = end_date
                
                # Calculate days remaining
                days_remaining = LicenseService.calculate_days_remaining(end_date_obj)
                
                QMessageBox.information(
                    self,
                    self.tr.get('license_activation_success'),
                    self.tr.format('license_activation_success_msg',
                        owner=owner,
                        start_date=start_date_obj.strftime('%d/%m/%Y'),
                        end_date=end_date_obj.strftime('%d/%m/%Y'),
                        days=days_remaining
                    )
                )
                logger.info(f"License activated: {owner}, expires: {end_date}")
                
                # Accept dialog - continue with app startup
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    self.tr.get('error_title'),
                    self.tr.get('license_save_failed')
                )
                self.btn_activate.setEnabled(True)
                self.btn_activate.setText(self.tr.get('license_btn_activate'))
                
        except Exception as e:
            QMessageBox.critical(
                self,
                self.tr.get('error_title'),
                f"{self.tr.get('license_problem_message')}\n\n{str(e)}"
            )
            logger.error(f"License activation error: {e}", exc_info=True)
            self.btn_activate.setEnabled(True)
            self.btn_activate.setText(self.tr.get('license_btn_activate'))
