# -*- coding: utf-8 -*-
"""
Cancel subscription dialog for Support CRM.
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QDateEdit, QPushButton, QGroupBox
)
from PySide6.QtCore import QDate

logger = logging.getLogger(__name__)


class CancelSubscriptionDialog(QDialog):
    """Dialog for cancelling a subscription."""
    
    def __init__(self, parent=None, family_name=""):
        """
        Initialize the cancel subscription dialog.
        
        Args:
            parent: Parent widget
            family_name: Name of the family for display
        """
        super().__init__(parent)
        self.setWindowTitle("Ακύρωση συνδρομής")
        self.setMinimumWidth(400)
        
        # Set app icon
        from utils.resource_loader import app_icon
        self.setWindowIcon(app_icon())
        
        self._init_ui(family_name)
        
        logger.debug("CancelSubscriptionDialog initialized")
    
    def _init_ui(self, family_name: str):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Info label
        if family_name:
            info_label = QLabel(f"Ακύρωση συνδρομής για: <b>{family_name}</b>")
            layout.addWidget(info_label)
        
        # Form group
        form_group = QGroupBox("Στοιχεία ακύρωσης")
        form_layout = QFormLayout()
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(10)
        
        # Cancel date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setDate(QDate.currentDate())
        form_layout.addRow("Ημερομηνία ακύρωσης:", self.date_edit)
        
        # Cancel reason
        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("π.χ. Αίτηση μέλους, οικονομικοί λόγοι...")
        form_layout.addRow("Αιτία (προαιρετικά):", self.reason_edit)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        btn_ok = QPushButton("Ακύρωση συνδρομής")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setDefault(True)
        button_layout.addWidget(btn_ok)
        
        btn_cancel = QPushButton("Άκυρο")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
    
    def get_data(self):
        """
        Get the cancellation data.
        
        Returns:
            Tuple of (cancel_date, reason)
        """
        cancel_date = self.date_edit.date().toPython()
        reason = self.reason_edit.text().strip()
        return cancel_date, reason
