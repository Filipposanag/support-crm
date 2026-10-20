# -*- coding: utf-8 -*-
"""
Subscription Email Tool Dialog - Manual bulk email sending for expiring subscriptions.
"""

import logging
from typing import List, Dict
from ui.utils.ui_helpers import gr_question
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QCheckBox, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QProgressDialog, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from services.subscription_service import SubscriptionService
from services.email_service import EmailService
from services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class SubscriptionEmailToolDialog(QDialog):
    """
    Dialog for manually sending subscription reminder emails.
    Allows preview and bulk sending of emails to families with expiring subscriptions.
    """
    
    def __init__(
        self,
        subscription_service: SubscriptionService,
        email_service: EmailService,
        settings_service: SettingsService,
        parent=None
    ):
        """
        Initialize dialog.
        
        Args:
            subscription_service: Subscription service instance
            email_service: Email service instance
            settings_service: Settings service instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.subscription_service = subscription_service
        self.email_service = email_service
        self.settings_service = settings_service
        
        self.subscriptions: List[Dict] = []
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("Αποστολή Email Συνδρομών")
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout(self)
        
        # Filters group
        filters_group = QGroupBox("Φίλτρα")
        filters_layout = QHBoxLayout()
        
        # Days before expiry
        filters_layout.addWidget(QLabel("Μέρες πριν τη λήξη:"))
        self.days_spinbox = QSpinBox()
        self.days_spinbox.setRange(1, 365)
        notification_config = self.settings_service.get_subscription_notification_config()
        self.days_spinbox.setValue(notification_config.get('days_before_expiration', 30))
        filters_layout.addWidget(self.days_spinbox)
        
        filters_layout.addSpacing(20)
        
        # Only unpaid checkbox
        self.only_unpaid_checkbox = QCheckBox("Μόνο όσοι χρωστάνε")
        self.only_unpaid_checkbox.setChecked(True)
        filters_layout.addWidget(self.only_unpaid_checkbox)
        
        filters_layout.addStretch()
        
        # Preview button
        self.preview_button = QPushButton("Προεπισκόπηση")
        self.preview_button.clicked.connect(self._preview_subscriptions)
        filters_layout.addWidget(self.preview_button)
        
        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)
        
        # Results label
        self.results_label = QLabel("Θα σταλούν 0 email")
        font = QFont()
        font.setBold(True)
        self.results_label.setFont(font)
        layout.addWidget(self.results_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Πελάτης", "Email", "Ημ. Λήξης", "Ποσό", "Πληρωμένο", "Υπόλοιπο"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)  # Stretch last column to fill space
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.send_button = QPushButton("Αποστολή Email")
        self.send_button.clicked.connect(self._send_emails)
        self.send_button.setEnabled(False)
        button_layout.addWidget(self.send_button)
        
        close_button = QPushButton("Κλείσιμο")
        close_button.clicked.connect(self.reject)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def _preview_subscriptions(self):
        """Preview subscriptions that will receive emails."""
        try:
            days = self.days_spinbox.value()
            only_unpaid = self.only_unpaid_checkbox.isChecked()
            
            # Get subscriptions
            self.subscriptions = self.subscription_service.get_subscriptions_expiring_in(
                days=days,
                only_unpaid=only_unpaid
            )
            
            # Update table
            self.table.setRowCount(len(self.subscriptions))
            
            for row, sub in enumerate(self.subscriptions):
                self.table.setItem(row, 0, QTableWidgetItem(sub['family_name']))
                self.table.setItem(row, 1, QTableWidgetItem(sub['email']))
                self.table.setItem(row, 2, QTableWidgetItem(str(sub['expiry_date'])))
                
                total_item = QTableWidgetItem(f"{sub['total_amount']:.2f}€")
                total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 3, total_item)
                
                paid_item = QTableWidgetItem(f"{sub['paid_amount']:.2f}€")
                paid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 4, paid_item)
                
                remaining_item = QTableWidgetItem(f"{sub['remaining_amount']:.2f}€")
                remaining_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 5, remaining_item)
            
            # Resize columns to fit content, except the last one which is stretched
            for col in range(self.table.columnCount() - 1):
                self.table.resizeColumnToContents(col)
            
            # Update label
            count = len(self.subscriptions)
            self.results_label.setText(f"Θα σταλούν {count} email")
            
            # Enable send button if there are subscriptions
            self.send_button.setEnabled(count > 0)
            
            logger.info(f"Preview: {count} subscriptions found")
            
        except Exception as e:
            logger.error(f"Error previewing subscriptions: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά την προεπισκόπηση:\n\n{str(e)}"
            )
    
    def _send_emails(self):
        """Send emails to all subscriptions in the list."""
        if not self.subscriptions:
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Δεν υπάρχουν συνδρομές για αποστολή email."
            )
            return
        
        # Confirm action
        reply = gr_question(
            self,
            "Επιβεβαίωση",
            f"Θέλετε να στείλετε {len(self.subscriptions)} email υπενθύμισης συνδρομής;",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Check if email is configured
        if not self.email_service.is_configured():
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Το email δεν έχει ρυθμιστεί. Παρακαλώ ρυθμίστε τις ρυθμίσεις SMTP στις Ρυθμίσεις."
            )
            return
        
        # Create progress dialog
        progress = QProgressDialog(
            "Αποστολή email...",
            "Ακύρωση",
            0,
            len(self.subscriptions),
            self
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        
        success_count = 0
        failed_count = 0
        failed_emails = []
        
        # Send emails
        for i, sub in enumerate(self.subscriptions):
            if progress.wasCanceled():
                break
            
            progress.setValue(i)
            progress.setLabelText(f"Αποστολή σε {sub['family_name']}...")
            
            try:
                # Prepare subscription data
                # Format expiry_date properly
                expiry_date_str = ''
                if sub.get('expiry_date'):
                    from datetime import datetime
                    expiry = sub['expiry_date']
                    if isinstance(expiry, str):
                        try:
                            expiry = datetime.strptime(expiry, '%Y-%m-%d').date()
                        except:
                            pass
                    if hasattr(expiry, 'strftime'):
                        expiry_date_str = expiry.strftime('%d/%m/%Y')
                    else:
                        expiry_date_str = str(expiry)
                else:
                    # Fallback: use payment_date if subscription_end_date is missing
                    if sub.get('payment_date'):
                        from datetime import datetime
                        payment_date = sub['payment_date']
                        if isinstance(payment_date, str):
                            try:
                                payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
                            except:
                                pass
                        if hasattr(payment_date, 'strftime'):
                            expiry_date_str = payment_date.strftime('%d/%m/%Y')
                        else:
                            expiry_date_str = str(payment_date)
                
                subscription_data = {
                    'family_name': sub['family_name'],
                    'expiry_date': expiry_date_str or 'Δεν έχει οριστεί',
                    'total_amount': f"{sub['total_amount']:.2f}",
                    'paid_amount': f"{sub['paid_amount']:.2f}",
                    'remaining_amount': f"{sub['remaining_amount']:.2f}"
                }
                
                # Send email
                success = self.email_service.send_subscription_reminder_email(
                    to_email=sub['email'],
                    subscription_data=subscription_data
                )
                
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                    failed_emails.append(f"{sub['family_name']} ({sub['email']})")
                
            except Exception as e:
                logger.error(f"Error sending email to {sub['email']}: {e}")
                failed_count += 1
                failed_emails.append(f"{sub['family_name']} ({sub['email']})")
        
        progress.setValue(len(self.subscriptions))
        
        # Show summary
        summary = f"Στάλθηκαν {success_count}/{len(self.subscriptions)} email."
        
        if failed_count > 0:
            summary += f"\n\n{failed_count} απέτυχαν:"
            for email in failed_emails[:10]:  # Show first 10
                summary += f"\n• {email}"
            if len(failed_emails) > 10:
                summary += f"\n... και {len(failed_emails) - 10} ακόμα"
        
        if failed_count > 0:
            QMessageBox.warning(self, "Ολοκληρώθηκε με σφάλματα", summary)
        else:
            QMessageBox.information(self, "Επιτυχία", summary)
        
        logger.info(f"Email sending complete: {success_count} success, {failed_count} failed")

