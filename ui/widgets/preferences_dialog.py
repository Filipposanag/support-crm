# -*- coding: utf-8 -*-
"""
Preferences Dialog
Dialog for managing user preferences including column visibility and locking.
"""

import logging
from typing import Optional, Dict, List
from ui.utils.ui_helpers import gr_question
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QGroupBox, QCheckBox, QPushButton, QDialogButtonBox,
    QWidget, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt

from services.settings_service import SettingsService, AppSettings
from utils.resource_loader import app_icon

logger = logging.getLogger(__name__)


class PreferencesDialog(QDialog):
    """Dialog for managing user preferences."""
    
    # Column definitions with Greek labels
    COLUMN_LABELS = {
        "families": {
            "code": "Κωδικός",
            "company_name": "Επωνυμία Εταιρείας",
            "last_name": "Επώνυμο",
            "first_name": "Όνομα",
            "phone": "Τηλέφωνο",
            "mobile": "Κινητό",
            "email": "Email",
            "city": "Πόλη",
            "address": "Διεύθυνση",
            "is_active": "Κατάσταση"
        },
        "payments": {
            "date": "Ημερομηνία",
            "family_code": "Κωδικός Πελάτη",
            "family_name": "Πελάτης",
            "description": "Περιγραφή",
            "total_amount": "Ποσό",
            "paid_amount": "Πληρωμένο",
            "remaining_amount": "Υπόλοιπο",
            "status": "Κατάσταση",
            "receipt_no": "Αριθμός Απόδειξης"
        },
        "subscriptions": {
            "code": "Κωδικός",
            "family_name": "Πελάτης",
            "year": "Ημερομηνία",
            "subscription_code": "Αρ. Συνδρομής",
            "receipt_no": "Αρ. Απόδειξης",
            "phone": "Τηλέφωνο",
            "total_amount": "Χρεωθέν",
            "paid_amount": "Πληρωμένο",
            "remaining_amount": "Υπόλοιπο",
            "start_date": "Έναρξη συνδρομής",
            "end_date": "Λήξη συνδρομής",
            "is_free": "Δωρεάν",
            "status": "Κατάσταση"
        },
        "reports": {
            "code": "Κωδικός",
            "family_name": "Πελάτης",
            "city": "Πόλη",
            "date": "Ημερομηνία",
            "charged": "Χρεωθέν",
            "paid": "Πληρωμένο",
            "remaining": "Υπόλοιπο"
        }
    }
    
    def __init__(
        self,
        settings_service: SettingsService,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize PreferencesDialog.
        
        Args:
            settings_service: SettingsService instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.settings_service = settings_service
        
        # Load current settings
        self.settings = settings_service.get_all_settings()
        if not self.settings:
            self.settings = AppSettings()
        
        # Storage for checkboxes
        self.column_checkboxes: Dict[str, Dict[str, QCheckBox]] = {
            "families": {},
            "payments": {},
            "subscriptions": {},
            "reports": {}
        }
        self.lock_checkboxes: Dict[str, QCheckBox] = {}
        
        self._init_ui()
        self._load_preferences()
        
        logger.debug("PreferencesDialog initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Προτιμήσεις")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs for each view
        self._create_view_tab("families", "Πελάτες")
        self._create_view_tab("payments", "Πληρωμές")
        self._create_view_tab("subscriptions", "Συνδρομές")
        self._create_view_tab("reports", "Αναφορές")
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        
        # Add reset button
        reset_btn = QPushButton("Επαναφορά προεπιλογών")
        reset_btn.clicked.connect(self._on_reset_defaults)
        button_box.addButton(reset_btn, QDialogButtonBox.ResetRole)
        
        layout.addWidget(button_box)
    
    def _create_view_tab(self, view_name: str, tab_label: str):
        """
        Create a tab for a specific view.
        
        Args:
            view_name: Internal view name ("families", "payments", "reports")
            tab_label: Display label for the tab
        """
        # Create tab widget
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(10, 10, 10, 10)
        tab_layout.setSpacing(10)
        
        # Visible columns group
        columns_group = QGroupBox("Ορατά πεδία")
        columns_layout = QVBoxLayout(columns_group)
        columns_layout.setSpacing(5)
        
        # Create scroll area for columns
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        scroll_layout.setSpacing(5)
        
        # Get column definitions for this view
        columns = self.COLUMN_LABELS.get(view_name, {})
        
        # Create checkbox for each column
        for key, label in columns.items():
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)  # Default to checked
            self.column_checkboxes[view_name][key] = checkbox
            scroll_layout.addWidget(checkbox)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        columns_layout.addWidget(scroll)
        
        tab_layout.addWidget(columns_group)
        
        # Column lock checkbox
        lock_checkbox = QCheckBox("Κλείδωμα πλάτους στηλών")
        lock_checkbox.setToolTip(
            "Όταν είναι ενεργό, το πλάτος των στηλών δεν μπορεί να αλλάξει"
        )
        self.lock_checkboxes[view_name] = lock_checkbox
        tab_layout.addWidget(lock_checkbox)
        
        tab_layout.addStretch()
        
        # Add tab to widget
        self.tab_widget.addTab(tab, tab_label)
    
    def _load_preferences(self):
        """Load current preferences from settings."""
        for view_name in ["families", "payments", "subscriptions", "reports"]:
            # Load visible columns
            visible_columns = self.settings.get_visible_columns(view_name)
            
            # Update checkboxes
            for key, checkbox in self.column_checkboxes[view_name].items():
                checkbox.setChecked(key in visible_columns)
            
            # Load lock status
            locked = self.settings.get_columns_locked(view_name)
            self.lock_checkboxes[view_name].setChecked(locked)
        
        logger.debug("Preferences loaded into dialog")
    
    def _on_accept(self):
        """Handle OK button click."""
        try:
            # Collect preferences from all tabs
            for view_name in ["families", "payments", "subscriptions", "reports"]:
                # Collect checked columns
                visible_columns = [
                    key for key, checkbox in self.column_checkboxes[view_name].items()
                    if checkbox.isChecked()
                ]
                
                # Ensure at least one column is visible
                if not visible_columns:
                    QMessageBox.warning(
                        self,
                        "Προειδοποίηση",
                        f"Πρέπει να επιλέξετε τουλάχιστον μία στήλη για την καρτέλα '{self._get_tab_label(view_name)}'."
                    )
                    return
                
                # Update settings
                self.settings.set_visible_columns(view_name, visible_columns)
                
                # Update lock status
                locked = self.lock_checkboxes[view_name].isChecked()
                self.settings.set_columns_locked(view_name, locked)
            
            # Save settings to database
            success = self.settings_service.save_settings(self.settings)
            
            if success:
                logger.info("Preferences saved successfully")
                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    "Αποτυχία αποθήκευσης προτιμήσεων."
                )
        
        except Exception as e:
            logger.error(f"Error saving preferences: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά την αποθήκευση προτιμήσεων:\n\n{str(e)}"
            )
    
    def _on_reset_defaults(self):
        """Handle reset to defaults button click."""
        reply = gr_question(
            self,
            "Επιβεβαίωση",
            "Είστε σίγουροι ότι θέλετε να επαναφέρετε όλες τις προτιμήσεις στις προεπιλεγμένες τιμές;",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset to defaults
            for view_name in ["families", "payments", "subscriptions", "reports"]:
                # Get default columns
                if view_name == "families":
                    default_columns = AppSettings.DEFAULT_FAMILIES_COLUMNS
                elif view_name == "payments":
                    default_columns = AppSettings.DEFAULT_PAYMENTS_COLUMNS
                elif view_name == "subscriptions":
                    default_columns = AppSettings.DEFAULT_SUBSCRIPTIONS_COLUMNS
                else:
                    default_columns = AppSettings.DEFAULT_REPORTS_COLUMNS
                
                # Check all default columns
                for key, checkbox in self.column_checkboxes[view_name].items():
                    checkbox.setChecked(key in default_columns)
                
                # Unlock columns
                self.lock_checkboxes[view_name].setChecked(False)
            
            logger.debug("Preferences reset to defaults")
    
    def _get_tab_label(self, view_name: str) -> str:
        """Get the display label for a view name."""
        labels = {
            "families": "Πελάτες",
            "payments": "Πληρωμές",
            "subscriptions": "Συνδρομές",
            "reports": "Αναφορές"
        }
        return labels.get(view_name, view_name)
