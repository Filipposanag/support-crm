# -*- coding: utf-8 -*-
"""
Send Receipt Email Dialog - Dialog for sending payment receipt via email.
"""

import logging
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QCheckBox, QPushButton, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt

from services.email_service import EmailService
from services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class SendReceiptEmailDialog(QDialog):
    """
    Dialog for sending payment receipt via email.
    Allows customization of subject and body before sending.
    """
    
    def __init__(
        self,
        email_service: EmailService,
        settings_service: SettingsService,
        to_email: str,
        payment_data: dict,
        pdf_path: Optional[str] = None,
        parent=None
    ):
        """
        Initialize dialog.
        
        Args:
            email_service: Email service instance
            settings_service: Settings service instance
            to_email: Recipient email address
            payment_data: Dictionary with payment info (family_name, payment_date, amount, receipt_no)
            pdf_path: Path to PDF receipt file (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        self.email_service = email_service
        self.settings_service = settings_service
        self.to_email = to_email
        self.payment_data = payment_data
        self.pdf_path = pdf_path
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("Αποστολή Απόδειξης με Email")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Email details group
        details_group = QGroupBox("Στοιχεία Email")
        details_layout = QVBoxLayout()
        
        # To field
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("Προς:"))
        self.to_edit = QLineEdit(self.to_email)
        self.to_edit.setPlaceholderText("email παραλήπτη")
        to_layout.addWidget(self.to_edit)
        details_layout.addLayout(to_layout)
        
        # Subject field
        subject_layout = QHBoxLayout()
        subject_layout.addWidget(QLabel("Θέμα:"))
        
        # Get template and replace placeholders
        receipt_config = self.settings_service.get_email_receipt_config()
        org_name = self.settings_service.get_org_name()
        
        subject_template = receipt_config.get('subject', 'Απόδειξη Πληρωμής')
        try:
            subject = subject_template.format(
                family_name=self.payment_data.get('family_name', ''),
                payment_date=self.payment_data.get('payment_date', ''),
                amount=self.payment_data.get('amount', ''),
                receipt_no=self.payment_data.get('receipt_no', ''),
                org_name=org_name
            )
        except KeyError:
            subject = subject_template
        
        self.subject_edit = QLineEdit(subject)
        subject_layout.addWidget(self.subject_edit)
        details_layout.addLayout(subject_layout)
        
        # Body field
        details_layout.addWidget(QLabel("Κείμενο:"))
        
        body_template = receipt_config.get('body', 'Σας αποστέλλουμε την απόδειξη πληρωμής σας.')
        try:
            body = body_template.format(
                family_name=self.payment_data.get('family_name', ''),
                payment_date=self.payment_data.get('payment_date', ''),
                amount=self.payment_data.get('amount', ''),
                receipt_no=self.payment_data.get('receipt_no', ''),
                org_name=org_name
            )
        except KeyError:
            body = body_template
        
        self.body_edit = QTextEdit()
        self.body_edit.setPlainText(body)
        self.body_edit.setMinimumHeight(200)
        details_layout.addWidget(self.body_edit)
        
        # Attach PDF checkbox
        self.attach_pdf_checkbox = QCheckBox("Επισύναψη PDF απόδειξης")
        self.attach_pdf_checkbox.setChecked(bool(self.pdf_path))
        self.attach_pdf_checkbox.setEnabled(bool(self.pdf_path))
        details_layout.addWidget(self.attach_pdf_checkbox)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        send_button = QPushButton("Αποστολή")
        send_button.clicked.connect(self._send_email)
        button_layout.addWidget(send_button)
        
        cancel_button = QPushButton("Άκυρο")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def _send_email(self):
        """Send the email."""
        try:
            # Check if email is configured
            if not self.email_service.is_configured():
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    "Το email δεν έχει ρυθμιστεί. Παρακαλώ ρυθμίστε τις ρυθμίσεις SMTP στις Ρυθμίσεις."
                )
                return
            
            # Get values
            recipient = self.to_edit.text().strip()
            subject = self.subject_edit.text().strip()
            body = self.body_edit.toPlainText().strip()

            if not recipient or "@" not in recipient or "." not in recipient.split("@")[-1]:
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    "Παρακαλώ δώστε έγκυρη διεύθυνση email παραλήπτη."
                )
                return

            if not subject or not body:
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    "Το θέμα και το κείμενο δεν μπορούν να είναι κενά."
                )
                return
            
            # Determine PDF path
            pdf_path = None
            if self.attach_pdf_checkbox.isChecked() and self.pdf_path:
                pdf_path = self.pdf_path
            
            # Send email
            success = self.email_service.send_receipt_email(
                to_email=recipient,
                payment_data=self.payment_data,
                pdf_path=pdf_path,
                custom_subject=subject,
                custom_body=body
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "Επιτυχία",
                    f"Το email στάλθηκε επιτυχώς στο {recipient}"
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    "Αποτυχία αποστολής email. Ελέγξτε τις ρυθμίσεις SMTP και τα logs."
                )
            
        except Exception as e:
            logger.error(f"Error sending receipt email: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά την αποστολή email:\n\n{str(e)}"
            )

