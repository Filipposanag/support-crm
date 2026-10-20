# -*- coding: utf-8 -*-
"""
License Info Dialog - Standalone dialog showing only license information and activation.
"""

import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from services.license_service import LicenseService
from services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class LicenseInfoDialog(QDialog):
    """
    Standalone dialog for license information and activation.
    Shows only the license tab content, not the full settings.
    """
    
    def __init__(self, settings_service: SettingsService, parent=None):
        """
        Initialize license info dialog.
        
        Args:
            settings_service: Settings service instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.settings_service = settings_service
        
        self.setWindowTitle("Άδεια Χρήσης")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self._init_ui()
        self._load_license_info()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Διαχείριση Άδειας Χρήσης")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # ========== License Information Section ==========
        info_group = QGroupBox("Πληροφορίες Άδειας")
        info_layout = QFormLayout()
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setVerticalSpacing(12)
        info_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Owner
        self.license_owner_label = QLabel("-")
        self.license_owner_label.setStyleSheet("font-weight: bold;")
        info_layout.addRow("Ιδιοκτήτης Άδειας:", self.license_owner_label)
        
        # Start date
        self.license_start_label = QLabel("-")
        info_layout.addRow("Ημ/νία Έναρξης:", self.license_start_label)
        
        # End date
        self.license_end_label = QLabel("-")
        info_layout.addRow("Ημ/νία Λήξης:", self.license_end_label)
        
        # Days remaining
        self.license_days_label = QLabel("-")
        self.license_days_label.setStyleSheet("font-weight: bold;")
        info_layout.addRow("Υπολειπόμενες Ημέρες:", self.license_days_label)
        
        # Status
        self.license_status_label = QLabel("-")
        self.license_status_label.setStyleSheet("font-weight: bold; padding: 6px; border-radius: 3px;")
        info_layout.addRow("Κατάσταση:", self.license_status_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # ========== License Activation Section ==========
        activation_group = QGroupBox("Ενεργοποίηση Άδειας")
        activation_layout = QVBoxLayout()
        activation_layout.setContentsMargins(16, 16, 16, 16)
        activation_layout.setSpacing(12)
        
        # Description
        activation_desc = QLabel(
            "Εισάγετε το κλειδί άδειας που σας παρέχεται για να ενεργοποιήσετε την εφαρμογή.\n"
            "Απαιτείται σύνδεση στο Internet για επικύρωση."
        )
        activation_desc.setWordWrap(True)
        activation_desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        activation_layout.addWidget(activation_desc)
        
        # License key input
        key_layout = QHBoxLayout()
        key_label = QLabel("Κλειδί Άδειας:")
        key_label.setMinimumWidth(100)
        self.license_key_input = QLineEdit()
        self.license_key_input.setPlaceholderText("Εισάγετε το κλειδί άδειας")
        self.license_key_input.setMinimumHeight(32)
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.license_key_input)
        activation_layout.addLayout(key_layout)
        
        # Activate button
        self.activate_license_btn = QPushButton("Ενεργοποίηση")
        self.activate_license_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;"
        )
        self.activate_license_btn.clicked.connect(self._activate_license)
        activation_layout.addWidget(self.activate_license_btn)
        
        activation_group.setLayout(activation_layout)
        layout.addWidget(activation_group)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Κλείσιμο")
        close_btn.setMinimumHeight(35)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    
    def _activate_license(self):
        """Activate license with provided key - requires online validation."""
        try:
            license_key = self.license_key_input.text().strip()
            
            if not license_key:
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    "Παρακαλώ εισάγετε κλειδί άδειας."
                )
                return
            
            # Disable button during validation
            self.activate_license_btn.setEnabled(False)
            self.activate_license_btn.setText("Επικύρωση online...")
            
            # Online validation required
            from services.license_validator import check_license_status
            import config
            
            validation_result = check_license_status(
                license_key=license_key,
                validation_url=config.LICENSE_VALIDATION_CONFIG['validation_url'],
                timeout=config.LICENSE_VALIDATION_CONFIG['timeout']
            )
            
            if validation_result['online']:
                # Server responded
                if validation_result['valid']:
                    # Valid license - use dates from server
                    owner = validation_result['owner_name']
                    start_date = validation_result['start_date']
                    end_date = validation_result['end_date']
                    logger.info(f"Online license validation successful: {owner}")
                else:
                    # Invalid or expired license
                    error_msg = validation_result.get('error', 'Το κλειδί άδειας δεν είναι έγκυρο.')
                    QMessageBox.critical(
                        self,
                        "Μη Έγκυρο Κλειδί",
                        error_msg
                    )
                    logger.warning(f"Invalid license key attempted: {license_key}")
                    self.activate_license_btn.setEnabled(True)
                    self.activate_license_btn.setText("Ενεργοποίηση")
                    return
            else:
                # No internet connection
                QMessageBox.critical(
                    self,
                    "Απαιτείται Σύνδεση Internet",
                    "Αδυναμία επικύρωσης άδειας online.\n\n"
                    "Η ενεργοποίηση άδειας απαιτεί σύνδεση στο Internet.\n\n"
                    "Παρακαλώ ελέγξτε τη σύνδεσή σας και δοκιμάστε ξανά."
                )
                logger.warning(f"License validation failed - no connection: {license_key}")
                self.activate_license_btn.setEnabled(True)
                self.activate_license_btn.setText("Ενεργοποίηση")
                return
            
            # Save license to database with server data
            if self.settings_service.set_license(
                license_key=license_key,
                owner=owner,
                start_date=start_date,
                end_date=end_date,
                status='active'
            ):
                # Format dates for display
                if isinstance(start_date, str):
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                else:
                    start_date_obj = start_date
                
                if isinstance(end_date, str):
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                else:
                    end_date_obj = end_date
                
                days_remaining = LicenseService.calculate_days_remaining(end_date_obj)
                
                QMessageBox.information(
                    self,
                    "Επιτυχής Ενεργοποίηση",
                    f"Η άδεια ενεργοποιήθηκε επιτυχώς!\n\n"
                    f"Ιδιοκτήτης: {owner}\n"
                    f"Ημ/νία Έναρξης: {start_date_obj.strftime('%d/%m/%Y')}\n"
                    f"Ημ/νία Λήξης: {end_date_obj.strftime('%d/%m/%Y')}\n\n"
                    f"Απομένουν {days_remaining} ημέρες."
                )
                logger.info(f"License activated: {owner}, expires: {end_date}")
                
                # Reload license info display
                self._load_license_info()
                
                # Clear input
                self.license_key_input.clear()
            else:
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    "Αποτυχία αποθήκευσης άδειας στη βάση δεδομένων."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα ενεργοποίησης άδειας:\n{str(e)}"
            )
            logger.error(f"License activation error: {e}", exc_info=True)
        finally:
            self.activate_license_btn.setEnabled(True)
            self.activate_license_btn.setText("Ενεργοποίηση")
    
    def _load_license_info(self):
        """Load and display license information."""
        try:
            license_info = self.settings_service.get_license_info()
            
            if not license_info or license_info['status'] == 'none':
                self.license_owner_label.setText("-")
                self.license_start_label.setText("-")
                self.license_end_label.setText("-")
                self.license_days_label.setText("-")
                self.license_status_label.setText("Δεν έχει οριστεί άδεια")
                self.license_status_label.setStyleSheet(
                    "font-weight: bold; padding: 6px; border-radius: 3px; "
                    "background-color: #f5f5f5; color: #757575;"
                )
                return
            
            # Display owner
            self.license_owner_label.setText(license_info['owner'] or "-")
            
            # Display dates
            start_date = license_info['start_date']
            end_date = license_info['end_date']
            
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if start_date:
                self.license_start_label.setText(start_date.strftime('%d/%m/%Y'))
            else:
                self.license_start_label.setText("-")
            
            if end_date:
                self.license_end_label.setText(end_date.strftime('%d/%m/%Y'))
                
                # Calculate days remaining
                days_remaining = LicenseService.calculate_days_remaining(end_date)
                
                if days_remaining < 0:
                    self.license_days_label.setText(f"{abs(days_remaining)} (έληξε)")
                    self.license_days_label.setStyleSheet("font-weight: bold; color: #d32f2f;")
                elif days_remaining <= 30:
                    self.license_days_label.setText(str(days_remaining))
                    self.license_days_label.setStyleSheet("font-weight: bold; color: #FF9800;")
                else:
                    self.license_days_label.setText(str(days_remaining))
                    self.license_days_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
                
                # Status
                status_text = LicenseService.get_license_status_text(license_info['status'], days_remaining)
                status_color = LicenseService.get_license_status_color(license_info['status'], days_remaining)
                
                self.license_status_label.setText(status_text)
                self.license_status_label.setStyleSheet(
                    f"font-weight: bold; padding: 6px; border-radius: 3px; "
                    f"background-color: {status_color}; color: white;"
                )
            else:
                self.license_end_label.setText("-")
                self.license_days_label.setText("-")
                self.license_status_label.setText("Άγνωστη κατάσταση")
                self.license_status_label.setStyleSheet(
                    "font-weight: bold; padding: 6px; border-radius: 3px; "
                    "background-color: #f5f5f5; color: #757575;"
                )
                
        except Exception as e:
            logger.error(f"Failed to load license info: {e}", exc_info=True)
