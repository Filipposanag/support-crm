# -*- coding: utf-8 -*-
"""
Client Form Dialog - Φόρμα Πελάτη
Dialog for creating and editing client records.
Διάλογος για δημιουργία και επεξεργασία εγγραφών πελατών.
"""

import logging
from ui.utils.ui_helpers import gr_question
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLineEdit, QTextEdit, QComboBox, QDoubleSpinBox,
    QPushButton, QLabel, QMessageBox, QDialogButtonBox, QCheckBox,
    QScrollArea, QWidget, QLayout, QSizePolicy, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from db.repositories.clients_repo import ClientsRepository
from ui.i18n import TranslationManager

logger = logging.getLogger(__name__)


def _fmt_hours_full(h):
    """Decimal hours -> readable Greek 'X ώρες Y λεπτά' (remaining shown as minutes)."""
    try:
        total_min = int(round(float(h or 0) * 60))
    except (TypeError, ValueError):
        total_min = 0
    if total_min <= 0:
        return "0 λεπτά"
    hh, mm = divmod(total_min, 60)
    wh = "ώρα" if hh == 1 else "ώρες"
    wm = "λεπτό" if mm == 1 else "λεπτά"
    if hh and mm:
        return f"{hh} {wh} {mm} {wm}"
    if hh:
        return f"{hh} {wh}"
    return f"{mm} {wm}"


def _fmt_hours_short(h):
    """Decimal hours -> compact 'Xω Yλ' for table cells."""
    try:
        total_min = int(round(float(h or 0) * 60))
    except (TypeError, ValueError):
        total_min = 0
    hh, mm = divmod(total_min, 60)
    if hh and mm:
        return f"{hh}ω {mm}λ"
    if hh:
        return f"{hh}ω"
    return f"{mm}λ"



class ClientForm(QDialog):
    """
    Dialog for creating and editing client records.
    Διάλογος για δημιουργία και επεξεργασία πελατών.
    """
    
    # Signal emitted when client is saved
    client_saved = Signal(int)  # Emits client_id
    
    # Signal emitted when a RustDesk session ends automatically
    session_ended = Signal()
    
    def __init__(
        self,
        clients_repo: ClientsRepository,
        tr_manager: TranslationManager,
        client_id: Optional[int] = None,
        parent=None
    ):
        """
        Initialize ClientForm.
        
        Args:
            clients_repo: ClientsRepository instance
            tr_manager: TranslationManager instance
            client_id: Optional client ID for editing (None for new client)
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.clients_repo = clients_repo
        self.tr_manager = tr_manager
        self.client_id = client_id
        
        # Get database connection from clients_repo
        self.db_connection = clients_repo.db if hasattr(clients_repo, 'db') else None
        
        # RustDesk launcher and session tracking
        from services.rustdesk_launcher import RustDeskLauncher
        from datetime import datetime
        self.rustdesk_launcher = RustDeskLauncher(self)
        self.session_start_time = None
        self.active_db_session_id = None
        self.session_timer = None
        
        self._init_ui()
        self._connect_signals()
        
        # Load client data if editing
        if self.client_id:
            self._load_client_data()
        else:
            # New client - set next available code
            self._set_next_code()
        
        logger.debug(f"ClientForm initialized (client_id={client_id})")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Set dialog properties
        if self.client_id:
            self.setWindowTitle(self.tr_manager.get('edit_client'))
        else:
            self.setWindowTitle(self.tr_manager.get('new_client'))
        
        # Set optimal size for comfortable viewing
        self.resize(1000, 750)
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Title
        title_label = QLabel(
            self.tr_manager.get('edit_client') if self.client_id 
            else self.tr_manager.get('new_client')
        )
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_details_tab()
        if self.client_id:
            # Only show package and financial tabs for existing clients
            self._create_package_tab()
            self._create_financial_tab()
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.button(QDialogButtonBox.Save).setText(self.tr_manager.get('btn_save'))
        button_box.button(QDialogButtonBox.Cancel).setText(self.tr_manager.get('btn_cancel'))
        main_layout.addWidget(button_box)
        
        self.button_box = button_box
    
    def _create_details_tab(self):
        """Create the details tab with client information."""
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Container widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Main Form - using QFormLayout
        form = QFormLayout()
        form.setContentsMargins(0, 10, 0, 10)
        form.setHorizontalSpacing(15)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        
        layout.addLayout(form)
        
        # RustDesk Section Header
        rustdesk_label = QLabel("RustDesk")
        rustdesk_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(rustdesk_label)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Αυτόματος")
        self.code_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow(self.tr_manager.get('client_code') + ":", self.code_input)
        
        # Company Name
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("Προαιρετικό")
        self.company_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow(self.tr_manager.get('company_name') + ":", self.company_input)
        
        # Last Name
        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Υποχρεωτικό")
        self.last_name_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow(self.tr_manager.get('last_name') + " *:", self.last_name_input)
        
        # First Name
        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("Υποχρεωτικό")
        self.first_name_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow(self.tr_manager.get('first_name') + " *:", self.first_name_input)
        
        # Phone & Mobile - using QGridLayout (4 columns: Label, Field, Label, Field)
        phone_mobile_grid = QGridLayout()
        phone_mobile_grid.setContentsMargins(0, 0, 0, 0)
        phone_mobile_grid.setHorizontalSpacing(10)
        phone_mobile_grid.setVerticalSpacing(0)
        
        phone_label = QLabel(self.tr_manager.get('phone') + ":")
        phone_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("π.χ. 2101234567")
        self.phone_input.setMinimumWidth(220)
        self.phone_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        mobile_label = QLabel(self.tr_manager.get('mobile') + ":")
        mobile_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("π.χ. 6971234567")
        self.mobile_input.setMinimumWidth(220)
        self.mobile_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        phone_mobile_grid.addWidget(phone_label, 0, 0)
        phone_mobile_grid.addWidget(self.phone_input, 0, 1)
        phone_mobile_grid.addWidget(mobile_label, 0, 2)
        phone_mobile_grid.addWidget(self.mobile_input, 0, 3)
        
        # Set column stretch: labels don't expand, fields do
        phone_mobile_grid.setColumnStretch(0, 0)
        phone_mobile_grid.setColumnStretch(1, 1)
        phone_mobile_grid.setColumnStretch(2, 0)
        phone_mobile_grid.setColumnStretch(3, 1)
        
        form.addRow(phone_mobile_grid)
        
        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("π.χ. email@example.com")
        self.email_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow(self.tr_manager.get('email') + ":", self.email_input)
        
        # Address
        self.address_input = QLineEdit()
        self.address_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow(self.tr_manager.get('address') + ":", self.address_input)
        
        # City & Postal Code - using QGridLayout
        city_postal_grid = QGridLayout()
        city_postal_grid.setContentsMargins(0, 0, 0, 0)
        city_postal_grid.setHorizontalSpacing(10)
        city_postal_grid.setVerticalSpacing(0)
        
        city_label = QLabel(self.tr_manager.get('city') + ":")
        city_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.city_input = QLineEdit()
        self.city_input.setMinimumWidth(200)
        self.city_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        postal_label = QLabel(self.tr_manager.get('postal_code') + ":")
        postal_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.postal_code_input = QLineEdit()
        self.postal_code_input.setMinimumWidth(140)
        self.postal_code_input.setMaximumWidth(180)  # Keep postal code narrow
        self.postal_code_input.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        city_postal_grid.addWidget(city_label, 0, 0)
        city_postal_grid.addWidget(self.city_input, 0, 1)
        city_postal_grid.addWidget(postal_label, 0, 2)
        city_postal_grid.addWidget(self.postal_code_input, 0, 3)
        
        # Set column stretch: city expands more, postal code less
        city_postal_grid.setColumnStretch(0, 0)
        city_postal_grid.setColumnStretch(1, 2)
        city_postal_grid.setColumnStretch(2, 0)
        city_postal_grid.setColumnStretch(3, 1)
        
        form.addRow(city_postal_grid)
        
        # Tax ID
        self.tax_id_input = QLineEdit()
        self.tax_id_input.setPlaceholderText("Α.Δ.Τ.")
        self.tax_id_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow(self.tr_manager.get('tax_id') + ":", self.tax_id_input)

        # ΑΦΜ (απαιτείται για τιμολόγιο)
        self.afm_input = QLineEdit()
        self.afm_input.setPlaceholderText("Απαιτείται για τιμολόγιο")
        self.afm_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow("ΑΦΜ:", self.afm_input)

        # ΔΟΥ (για τιμολόγιο)
        self.doy_input = QLineEdit()
        self.doy_input.setPlaceholderText("Προαιρετικό")
        self.doy_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form.addRow("ΔΟΥ:", self.doy_input)
        
        layout.addLayout(form)
        
        # RustDesk Section Header
        rustdesk_label = QLabel("RustDesk")
        rustdesk_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(rustdesk_label)
        
        # RustDesk Form
        rustdesk_form = QFormLayout()
        rustdesk_form.setContentsMargins(0, 5, 0, 10)
        rustdesk_form.setHorizontalSpacing(15)
        rustdesk_form.setVerticalSpacing(12)
        rustdesk_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        rustdesk_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        rustdesk_form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        
        # RustDesk ID & Password - using QGridLayout
        rustdesk_grid = QGridLayout()
        rustdesk_grid.setContentsMargins(0, 0, 0, 0)
        rustdesk_grid.setHorizontalSpacing(10)
        rustdesk_grid.setVerticalSpacing(0)
        
        rustdesk_id_label = QLabel(self.tr_manager.get('rustdesk_id') + ":")
        rustdesk_id_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.rustdesk_id_input = QLineEdit()
        self.rustdesk_id_input.setPlaceholderText("π.χ. 123456789")
        self.rustdesk_id_input.setMinimumWidth(180)
        self.rustdesk_id_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # RustDesk Connect Button
        from resources.icons import get_icon
        self.rustdesk_connect_btn = QPushButton(get_icon('settings'), "Σύνδεση")
        self.rustdesk_connect_btn.setStyleSheet("QPushButton{background-color:#4CAF50;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#45a049;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        self.rustdesk_connect_btn.setEnabled(False)  # Disabled until ID is entered
        self.rustdesk_connect_btn.setToolTip("Σύνδεση μέσω RustDesk")
        
        password_label = QLabel(self.tr_manager.get('rustdesk_password') + ":")
        password_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.rustdesk_password_input = QLineEdit()
        self.rustdesk_password_input.setEchoMode(QLineEdit.Password)
        self.rustdesk_password_input.setPlaceholderText("Προαιρετικό")
        self.rustdesk_password_input.setMinimumWidth(180)
        self.rustdesk_password_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        rustdesk_grid.addWidget(rustdesk_id_label, 0, 0)
        rustdesk_grid.addWidget(self.rustdesk_id_input, 0, 1)
        rustdesk_grid.addWidget(self.rustdesk_connect_btn, 0, 2)
        rustdesk_grid.addWidget(password_label, 0, 3)
        rustdesk_grid.addWidget(self.rustdesk_password_input, 0, 4)
        
        # Set column stretch: labels and button don't expand, fields do
        rustdesk_grid.setColumnStretch(0, 0)
        rustdesk_grid.setColumnStretch(1, 1)
        rustdesk_grid.setColumnStretch(2, 0)  # button
        rustdesk_grid.setColumnStretch(3, 0)
        rustdesk_grid.setColumnStretch(4, 1)
        
        rustdesk_form.addRow(rustdesk_grid)
        
        layout.addLayout(rustdesk_form)
        
        # (Το «Πλάνο Υποστήριξης»/ανάθεση πακέτου αφαιρέθηκε από τη φόρμα.
        #  Τα πακέτα προστίθενται πλέον ΜΟΝΟ από την Καρτέλα Πελάτη -> «Προσθήκη Πακέτου».)
        
        # Notes Section Header
        notes_label = QLabel(self.tr_manager.get('notes'))
        notes_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(notes_label)
        
        # Notes Form
        notes_form = QFormLayout()
        notes_form.setContentsMargins(0, 5, 0, 10)
        notes_form.setHorizontalSpacing(15)
        notes_form.setVerticalSpacing(12)
        notes_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        notes_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        notes_form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        
        # General Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setPlaceholderText("Γενικές σημειώσεις...")
        self.notes_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        notes_form.addRow("Γενικές:", self.notes_input)
        
        # Support Notes
        self.support_notes_input = QTextEdit()
        self.support_notes_input.setMaximumHeight(80)
        self.support_notes_input.setPlaceholderText("Σημειώσεις υποστήριξης...")
        self.support_notes_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        notes_form.addRow("Υποστήριξης:", self.support_notes_input)
        
        layout.addLayout(notes_form)
        
        # Active checkbox
        self.active_checkbox = QCheckBox(self.tr_manager.get('active'))
        self.active_checkbox.setChecked(True)
        layout.addWidget(self.active_checkbox)
        
        layout.addStretch()
        
        # Set container to scroll area
        scroll.setWidget(container)
        
        # Add tab
        self.tab_widget.addTab(scroll, "📋 Στοιχεία")
    
    def _create_package_tab(self):
        """Create the package tab showing package information and hours balance."""
        # Container widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Package Information Section
        package_header = QLabel("📦 Πληροφορίες Πακέτου")
        package_header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(package_header)
        
        # Package details container
        self.package_info_widget = QWidget()
        package_layout = QVBoxLayout(self.package_info_widget)
        package_layout.setContentsMargins(0, 0, 0, 0)
        package_layout.setSpacing(10)
        
        # Will be populated in _load_package_info
        self.package_name_label = QLabel("Φόρτωση...")
        self.package_name_label.setStyleSheet("font-size: 13px;")
        package_layout.addWidget(self.package_name_label)
        
        layout.addWidget(self.package_info_widget)
        
        # Hours Balance Section
        hours_header = QLabel("⏱️ Υπόλοιπο Ωρών")
        hours_header.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(hours_header)
        
        # Hours table
        self.hours_table = QTableWidget()
        self.hours_table.setColumnCount(6)
        self.hours_table.setHorizontalHeaderLabels([
            "Πακέτο", "Συνολικές Ώρες", "Χρησιμοποιημένες", "Υπόλοιπο", "Ημ. Αγοράς", "Λήξη"
        ])
        self.hours_table.horizontalHeader().setStretchLastSection(True)
        self.hours_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.hours_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.hours_table.setAlternatingRowColors(True)
        self.hours_table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.hours_table)
        
        # Summary labels
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(20)
        
        self.total_hours_summary = QLabel()
        self.total_hours_summary.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                color: #1976D2;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        summary_layout.addWidget(self.total_hours_summary)
        
        self.used_hours_summary = QLabel()
        self.used_hours_summary.setStyleSheet("""
            QLabel {
                background-color: #FFF3E0;
                color: #E65100;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        summary_layout.addWidget(self.used_hours_summary)
        
        self.remaining_hours_summary = QLabel()
        self.remaining_hours_summary.setStyleSheet("""
            QLabel {
                background-color: #E8F5E9;
                color: #2E7D32;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        summary_layout.addWidget(self.remaining_hours_summary)
        
        layout.addLayout(summary_layout)
        
        layout.addStretch()
        
        # Add tab
        self.tab_widget.addTab(container, "📦 Πακέτο")
        
        # Load package data
        if self.client_id:
            self._load_package_info()
    
    def _create_financial_tab(self):
        """Create the financial tab showing payments history."""
        # Container widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        financial_header = QLabel("💰 Οικονομική Καρτέλα")
        financial_header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(financial_header)
        
        # Summary section
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(15)
        
        self.total_paid_label = QLabel()
        self.total_paid_label.setStyleSheet("""
            QLabel {
                background-color: #E8F5E9;
                color: #2E7D32;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #4CAF50;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        summary_layout.addWidget(self.total_paid_label)
        
        self.total_pending_label = QLabel()
        self.total_pending_label.setStyleSheet("""
            QLabel {
                background-color: #FFF3E0;
                color: #E65100;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #FF9800;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        summary_layout.addWidget(self.total_pending_label)
        
        self.total_amount_label = QLabel()
        self.total_amount_label.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                color: #1976D2;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #2196F3;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        summary_layout.addWidget(self.total_amount_label)
        
        layout.addLayout(summary_layout)
        
        # Payments table
        payments_header = QLabel("📋 Ιστορικό Πληρωμών")
        payments_header.setStyleSheet("font-size: 13px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(payments_header)
        
        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(6)
        self.payments_table.setHorizontalHeaderLabels([
            "Ημερομηνία", "Περιγραφή", "Συνολικό", "Πληρωμένο", "Υπόλοιπο", "Κατάσταση"
        ])
        self.payments_table.horizontalHeader().setStretchLastSection(True)
        self.payments_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.payments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.payments_table.setAlternatingRowColors(True)
        self.payments_table.verticalHeader().setVisible(False)
        
        # Set column widths
        header = self.payments_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Date
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Description
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Total
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Paid
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Remaining
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Status
        
        layout.addWidget(self.payments_table)
        
        layout.addStretch()
        
        # Add tab
        self.tab_widget.addTab(container, "💰 Οικονομικά")
        
        # Load financial data
        if self.client_id:
            self._load_financial_data()
    
    def _load_package_info(self):
        """Load and display package information for the client."""
        if not self.client_id or not self.db_connection:
            return
        
        try:
            # Get active package hours
            query = """
                SELECT 
                    cph.id,
                    cph.total_hours,
                    cph.used_hours,
                    cph.remaining_hours,
                    cph.purchase_date,
                    cph.expiry_date,
                    sp.name as package_name,
                    sp.package_type,
                    sp.price
                FROM client_package_hours cph
                LEFT JOIN support_packages sp ON cph.package_id = sp.id
                WHERE cph.client_id = %s
                AND cph.is_active = 1
                ORDER BY cph.purchase_date DESC
            """
            
            results = self.db_connection.execute_query(query, (self.client_id,))
            
            # Clear table
            self.hours_table.setRowCount(0)
            
            total_hours = 0.0
            total_used = 0.0
            total_remaining = 0.0
            
            if results and len(results) > 0:
                # Populate table
                for row_idx, row in enumerate(results):
                    self.hours_table.insertRow(row_idx)
                    
                    package_name = row.get('package_name', 'N/A')
                    total_h = float(row.get('total_hours', 0))
                    used_h = float(row.get('used_hours', 0))
                    remaining_h = float(row.get('remaining_hours', 0))
                    purchase_date = row.get('purchase_date')
                    expiry_date = row.get('expiry_date')
                    
                    total_hours += total_h
                    total_used += used_h
                    total_remaining += remaining_h
                    
                    self.hours_table.setItem(row_idx, 0, QTableWidgetItem(package_name))
                    self.hours_table.setItem(row_idx, 1, QTableWidgetItem(_fmt_hours_short(total_h)))
                    self.hours_table.setItem(row_idx, 2, QTableWidgetItem(_fmt_hours_short(used_h)))
                    self.hours_table.setItem(row_idx, 3, QTableWidgetItem(_fmt_hours_short(remaining_h)))
                    self.hours_table.setItem(row_idx, 4, QTableWidgetItem(
                        purchase_date.strftime('%d/%m/%Y') if purchase_date else 'N/A'
                    ))
                    self.hours_table.setItem(row_idx, 5, QTableWidgetItem(
                        expiry_date.strftime('%d/%m/%Y') if expiry_date else 'N/A'
                    ))
                
                # Update package info
                first_package = results[0]
                package_name = first_package.get('package_name', 'N/A')
                package_type = first_package.get('package_type', 'N/A')
                package_price = float(first_package.get('price', 0))
                
                self.package_name_label.setText(
                    f"Τρέχον Πακέτο: {package_name} ({package_type})\n"
                    f"Τιμή: {package_price:.2f} €"
                )
            else:
                self.package_name_label.setText("Δεν υπάρχει ενεργό πακέτο")
            
            # Update summary labels
            self.total_hours_summary.setText(f"Συνολικές: {_fmt_hours_full(total_hours)}")
            self.used_hours_summary.setText(f"Χρησιμοποιημένες: {_fmt_hours_full(total_used)}")
            self.remaining_hours_summary.setText(f"Υπόλοιπο: {_fmt_hours_full(total_remaining)}")
            
            logger.debug(f"Loaded package info for client {self.client_id}")
            
        except Exception as e:
            logger.error(f"Error loading package info: {e}")
            self.package_name_label.setText("⚠️ Σφάλμα φόρτωσης πακέτου")
    
    def _load_financial_data(self):
        """Load and display financial data (payments) for the client."""
        if not self.client_id or not self.db_connection:
            return
        
        try:
            # Get all payments for this client
            query = """
                SELECT 
                    payment_date,
                    description,
                    total_amount,
                    paid_amount,
                    remaining_amount,
                    status
                FROM payments
                WHERE family_id = %s
                ORDER BY payment_date DESC
            """
            
            results = self.db_connection.execute_query(query, (self.client_id,))
            
            # Clear table
            self.payments_table.setRowCount(0)
            
            total_paid = 0.0
            total_pending = 0.0
            total_amount = 0.0
            
            if results and len(results) > 0:
                # Populate table
                for row_idx, row in enumerate(results):
                    self.payments_table.insertRow(row_idx)
                    
                    payment_date = row.get('payment_date')
                    description = row.get('description', '')
                    total_amt = float(row.get('total_amount', 0))
                    paid_amt = float(row.get('paid_amount', 0))
                    remaining_amt = float(row.get('remaining_amount', 0))
                    status = row.get('status', '')
                    
                    total_amount += total_amt
                    total_paid += paid_amt
                    total_pending += remaining_amt
                    
                    # Date
                    date_item = QTableWidgetItem(
                        payment_date.strftime('%d/%m/%Y') if payment_date else 'N/A'
                    )
                    self.payments_table.setItem(row_idx, 0, date_item)
                    
                    # Description
                    self.payments_table.setItem(row_idx, 1, QTableWidgetItem(description))
                    
                    # Total amount
                    total_item = QTableWidgetItem(f"{total_amt:.2f} €")
                    total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.payments_table.setItem(row_idx, 2, total_item)
                    
                    # Paid amount
                    paid_item = QTableWidgetItem(f"{paid_amt:.2f} €")
                    paid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.payments_table.setItem(row_idx, 3, paid_item)
                    
                    # Remaining amount
                    remaining_item = QTableWidgetItem(f"{remaining_amt:.2f} €")
                    remaining_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.payments_table.setItem(row_idx, 4, remaining_item)
                    
                    # Status
                    _st = str(status or '').strip().lower()
                    status_text = {
                        'paid': '✅ Πληρωμένο',
                        'partial': '⚠️ Μερική πληρωμή',
                        'unpaid': '❌ Ανεξόφλητο',
                        'pending': '⏳ Σε εκκρεμότητα',
                        'cancelled': '🚫 Ακυρωμένο',
                        'canceled': '🚫 Ακυρωμένο',
                        'completed': '✅ Ολοκληρωμένο',
                        'overdue': '❗ Ληξιπρόθεσμο',
                        '': '—',
                    }.get(_st, 'Άγνωστη')
                    self.payments_table.setItem(row_idx, 5, QTableWidgetItem(status_text))
            
            # Update summary labels
            self.total_paid_label.setText(f"✅ Πληρωμένο\n{total_paid:.2f} €")
            self.total_pending_label.setText(f"⚠️ Υπόλοιπο\n{total_pending:.2f} €")
            self.total_amount_label.setText(f"💰 Σύνολο\n{total_amount:.2f} €")
            
            logger.debug(f"Loaded financial data for client {self.client_id}")
            
        except Exception as e:
            logger.error(f"Error loading financial data: {e}")
            QMessageBox.warning(
                self,
                "Σφάλμα",
                f"Σφάλμα φόρτωσης οικονομικών δεδομένων: {str(e)}"
            )
    
    def _connect_signals(self):
        """Connect signals to slots."""
        self.button_box.accepted.connect(self._on_save)
        self.button_box.rejected.connect(self.reject)
        
        # Enable/disable RustDesk connect button based on ID
        self.rustdesk_id_input.textChanged.connect(self._on_rustdesk_id_changed)
        
        # RustDesk connect button
        self.rustdesk_connect_btn.clicked.connect(self._on_rustdesk_connect)
        
        # RustDesk launcher signals
        self.rustdesk_launcher.process_started.connect(self._on_rustdesk_started)
        self.rustdesk_launcher.process_finished.connect(self._on_rustdesk_finished)
        self.rustdesk_launcher.process_error.connect(self._on_rustdesk_error)
    
    def _set_next_code(self):
        """Set the next available client code."""
        try:
            next_code = self.clients_repo.get_next_code()
            self.code_input.setText(str(next_code))
        except Exception as e:
            logger.error(f"Error getting next code: {e}")
            self.code_input.setText("1")
    
    def _load_support_packages(self):
        """Load support packages from database for new client."""
        if not self.db_connection:
            logger.warning("Cannot load support packages - no database connection")
            return
        
        try:
            query = """
                SELECT id, name, package_type, price
                FROM support_packages
                WHERE is_active = 1
                ORDER BY package_type, name
            """
            packages = self.db_connection.execute_query(query)
            
            for package in packages:
                package_id = package.get('id')
                name = package.get('name', '')
                price = float(package.get('price', 0))
                pkg_type = package.get('package_type', '')
                
                # Display format: "Name (€price)"
                display_text = f"{name} ({price:.2f} €)"
                
                # Store package data as tuple: (id, type)
                self.plan_combo.addItem(display_text, (package_id, pkg_type))
            
            logger.debug(f"Loaded {len(packages)} support packages for new client")
            
        except Exception as e:
            logger.error(f"Error loading support packages: {e}")
    
    def _load_client_data(self):
        """Load client data for editing."""
        try:
            client = self.clients_repo.get_client_by_id(self.client_id)
            if not client:
                QMessageBox.warning(
                    self,
                    self.tr_manager.get('warning'),
                    "Ο πελάτης δεν βρέθηκε"
                )
                self.reject()
                return
            
            # Populate fields
            self.code_input.setText(str(client.get('legacy_code', '')))
            self.company_input.setText(client.get('company_name', ''))
            self.last_name_input.setText(client.get('last_name', ''))
            self.first_name_input.setText(client.get('first_name', ''))
            self.phone_input.setText(client.get('phone', ''))
            self.mobile_input.setText(client.get('mobile', ''))
            self.email_input.setText(client.get('email', ''))
            self.address_input.setText(client.get('address', ''))
            self.city_input.setText(client.get('city', ''))
            self.postal_code_input.setText(client.get('postal_code', ''))
            self.tax_id_input.setText(client.get('national_id', ''))
            self.afm_input.setText(client.get('afm', ''))
            self.doy_input.setText(client.get('doy', ''))
            
            # RustDesk
            self.rustdesk_id_input.setText(client.get('rustdesk_id', ''))
            self.rustdesk_password_input.setText(client.get('rustdesk_password', ''))
            
            # Support Plan (editable in edit mode)
            if hasattr(self, 'plan_combo_edit'):
                plan = client.get('support_plan', 'hourly')
                # Find and select the matching plan
                for i in range(self.plan_combo_edit.count()):
                    if self.plan_combo_edit.itemData(i) == plan:
                        self.plan_combo_edit.setCurrentIndex(i)
                        break

            # Populate per-client hourly rate
            if hasattr(self, 'hourly_rate_input'):
                try:
                    self.hourly_rate_input.setValue(float(client.get('hourly_rate') or 0))
                except (TypeError, ValueError):
                    self.hourly_rate_input.setValue(0.0)
            
            # Notes
            self.notes_input.setPlainText(client.get('notes', ''))
            self.support_notes_input.setPlainText(client.get('notes_support', ''))
            
            # Active
            self.active_checkbox.setChecked(bool(client.get('is_active', 1)))
            
            # Load package hours balance (edit mode only)
            if hasattr(self, 'package_hours_label'):
                self._load_package_hours_balance()
            
            logger.debug(f"Loaded client data for ID {self.client_id}")
            
        except Exception as e:
            logger.error(f"Error loading client data: {e}")
            QMessageBox.critical(
                self,
                self.tr_manager.get('error'),
                f"Σφάλμα φόρτωσης δεδομένων: {str(e)}"
            )
            self.reject()
    
    def _validate_form(self) -> bool:
        """Validate form data."""
        # Check required fields
        if not self.last_name_input.text().strip():
            QMessageBox.warning(
                self,
                self.tr_manager.get('warning'),
                "Το επώνυμο είναι υποχρεωτικό"
            )
            self.last_name_input.setFocus()
            return False
        
        if not self.first_name_input.text().strip():
            QMessageBox.warning(
                self,
                self.tr_manager.get('warning'),
                "Το όνομα είναι υποχρεωτικό"
            )
            self.first_name_input.setFocus()
            return False
        
        return True
    
    def _load_package_hours_balance(self):
        """Load and display package hours balance for the client (legacy method for details tab)."""
        if not self.client_id or not self.db_connection:
            return
        
        # Only update if we have the label (edit mode in details tab)
        if not hasattr(self, 'package_hours_label'):
            return
        
        try:
            query = """
                SELECT SUM(remaining_hours) as total_hours
                FROM client_package_hours
                WHERE client_id = %s
                AND is_active = 1
                AND (expiry_date IS NULL OR expiry_date >= CURDATE())
            """
            
            results = self.db_connection.execute_query(query, (self.client_id,))
            
            if results and len(results) > 0:
                total_hours = results[0].get('total_hours')
                
                if total_hours is not None and total_hours > 0:
                    total_hours = float(total_hours)
                    
                    # Color code based on hours remaining
                    if total_hours >= 5:
                        bg_color = "#E8F5E9"  # Green
                        border_color = "#4CAF50"
                        text_color = "#2E7D32"
                        icon = "✅"
                    elif total_hours >= 2:
                        bg_color = "#FFF3E0"  # Orange
                        border_color = "#FF9800"
                        text_color = "#E65100"
                        icon = "⚠️"
                    else:
                        bg_color = "#FFEBEE"  # Red
                        border_color = "#F44336"
                        text_color = "#C62828"
                        icon = "🔴"
                    
                    self.package_hours_label.setStyleSheet(f"""
                        QLabel {{
                            background-color: {bg_color};
                            color: {text_color};
                            padding: 10px;
                            border-radius: 5px;
                            border-left: 4px solid {border_color};
                            font-weight: bold;
                        }}
                    """)
                    self.package_hours_label.setText(
                        f"{icon} {_fmt_hours_full(total_hours)} διαθέσιμες\n"
                        f"(Δείτε λεπτομέρειες στην καρτέλα 'Πακέτο')"
                    )
                else:
                    self.package_hours_label.setStyleSheet("""
                        QLabel {
                            background-color: #F5F5F5;
                            color: #757575;
                            padding: 10px;
                            border-radius: 5px;
                            border-left: 4px solid #BDBDBD;
                        }
                    """)
                    self.package_hours_label.setText("📦 Δεν υπάρχουν προπληρωμένες ώρες")
            else:
                self.package_hours_label.setStyleSheet("""
                    QLabel {
                        background-color: #F5F5F5;
                        color: #757575;
                        padding: 10px;
                        border-radius: 5px;
                        border-left: 4px solid #BDBDBD;
                    }
                """)
                self.package_hours_label.setText("📦 Δεν υπάρχουν προπληρωμένες ώρες")
                
            logger.debug(f"Loaded package hours balance for client {self.client_id}")
            
        except Exception as e:
            logger.error(f"Error loading package hours balance: {e}")
            self.package_hours_label.setText("⚠️ Σφάλμα φόρτωσης υπολοίπου")
    
    def _on_save(self):
        """Handle save button click."""
        if not self._validate_form():
            return
        
        try:
            # Prepare client data
            client_data = {
                'legacy_code': int(self.code_input.text()) if self.code_input.text().isdigit() else 0,
                'company_name': self.company_input.text().strip(),
                'last_name': self.last_name_input.text().strip(),
                'first_name': self.first_name_input.text().strip(),
                'phone': self.phone_input.text().strip(),
                'mobile': self.mobile_input.text().strip(),
                'email': self.email_input.text().strip(),
                'address': self.address_input.text().strip(),
                'city': self.city_input.text().strip(),
                'postal_code': self.postal_code_input.text().strip(),
                'national_id': self.tax_id_input.text().strip(),
                'afm': self.afm_input.text().strip(),
                'doy': self.doy_input.text().strip(),
                'rustdesk_id': self.rustdesk_id_input.text().strip(),
                'rustdesk_password': self.rustdesk_password_input.text().strip(),
                'notes': self.notes_input.toPlainText().strip(),
                'notes_support': self.support_notes_input.toPlainText().strip(),
                'is_active': 1 if self.active_checkbox.isChecked() else 0,
            }
            
            # For new clients, add support_plan from selected package
            if not self.client_id and hasattr(self, 'plan_combo'):
                package_data = self.plan_combo.currentData()
                if package_data and len(package_data) == 2:
                    package_id, pkg_type = package_data
                    client_data['support_plan'] = pkg_type
                    logger.debug(f"Setting initial support_plan: {pkg_type}")
            
            # For existing clients, update support_plan from dropdown
            if self.client_id and hasattr(self, 'plan_combo_edit'):
                selected_plan = self.plan_combo_edit.currentData()
                if selected_plan:
                    client_data['support_plan'] = selected_plan
                    logger.debug(f"Updating support_plan: {selected_plan}")

            # Per-client hourly rate override
            if hasattr(self, 'hourly_rate_input'):
                client_data['hourly_rate'] = round(float(self.hourly_rate_input.value()), 2)
            
            # Save client
            if self.client_id:
                # Update existing
                success = self.clients_repo.update_client(self.client_id, client_data)
                if success:
                    QMessageBox.information(
                        self,
                        self.tr_manager.get('success'),
                        self.tr_manager.get('msg_client_saved')
                    )
                    self.client_saved.emit(self.client_id)
                    self.accept()
                else:
                    QMessageBox.warning(
                        self,
                        self.tr_manager.get('warning'),
                        "Αποτυχία ενημέρωσης πελάτη"
                    )
            else:
                # Create new
                client_id = self.clients_repo.create_client(client_data)
                if client_id:
                    # Check if package was selected
                    package_data = self.plan_combo.currentData() if hasattr(self, 'plan_combo') else None
                    
                    if package_data and len(package_data) == 2:
                        # Package was selected - ask if user wants to create payment
                        package_id, pkg_type = package_data
                        
                        # Get package details
                        try:
                            query = "SELECT name, price, duration_months FROM support_packages WHERE id = %s"
                            packages = self.db_connection.execute_query(query, (package_id,))
                            
                            if packages and len(packages) > 0:
                                package = packages[0]
                                package_name = package.get('name', '')
                                package_price = float(package.get('price', 0))
                                
                                reply = gr_question(
                                    self,
                                    "Δημιουργία Πληρωμής",
                                    f"Ο πελάτης δημιουργήθηκε επιτυχώς!\n\n"
                                    f"Επιλέξατε το πακέτο: {package_name} ({package_price:.2f} €)\n\n"
                                    f"Θέλετε να δημιουργήσετε αμέσως πληρωμή για αυτό το πακέτο;\n\n"
                                    f"(Αν επιλέξετε 'Όχι', μπορείτε να δημιουργήσετε την πληρωμή αργότερα από το tab Πληρωμές)",
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.Yes
                                )
                                
                                if reply == QMessageBox.Yes:
                                    # Open payment form with pre-filled data
                                    self._create_payment_for_package(client_id, package_id, package_name, package_price)
                        except Exception as e:
                            logger.error(f"Error checking package details: {e}")
                    
                    QMessageBox.information(
                        self,
                        self.tr_manager.get('success'),
                        self.tr_manager.get('msg_client_saved')
                    )
                    self.client_saved.emit(client_id)
                    self.accept()
                else:
                    QMessageBox.warning(
                        self,
                        self.tr_manager.get('warning'),
                        "Αποτυχία δημιουργίας πελάτη"
                    )
                    
        except Exception as e:
            logger.error(f"Error saving client: {e}")
            QMessageBox.critical(
                self,
                self.tr_manager.get('error'),
                f"Σφάλμα αποθήκευσης: {str(e)}"
            )

    def _create_payment_for_package(self, client_id: int, package_id: int, package_name: str, package_price: float):
        """
        Create a payment for the selected package.
        
        Args:
            client_id: ID of the client
            package_id: ID of the support package
            package_name: Name of the package
            package_price: Price of the package
        """
        try:
            from datetime import date, timedelta
            from db.repositories.payments_repo import PaymentsRepository
            
            # Get package details for duration and prepaid hours
            query = "SELECT duration_months, prepaid_hours FROM support_packages WHERE id = %s"
            packages = self.db_connection.execute_query(query, (package_id,))
            
            if not packages or len(packages) == 0:
                logger.error(f"Package {package_id} not found")
                return
            
            duration_months = packages[0].get('duration_months', 12)
            prepaid_hours = packages[0].get('prepaid_hours')
            
            # Calculate dates
            today = date.today()
            end_date = today + timedelta(days=duration_months * 30)  # Approximate
            
            # Create payment data
            payment_data = {
                'family_id': client_id,
                'payment_date': today,
                'description': f'Πληρωμή Πακέτου: {package_name}',
                'receipt_no': f'PKG-{today.year}-{client_id}',
                'total_amount': package_price,
                'paid_amount': package_price,
                'remaining_amount': 0.00,
                'status': 'paid',
                'year': today.year,
                'support_package': str(package_id),
                'subscription_start_date': today,
                'subscription_end_date': end_date
            }
            
            # Create payment
            payments_repo = PaymentsRepository(self.db_connection)
            payment_id = payments_repo.create_payment(payment_data)
            
            if payment_id:
                # If package has prepaid hours, create client_package_hours record
                if prepaid_hours is not None and prepaid_hours > 0:
                    try:
                        hours_query = """
                            INSERT INTO client_package_hours (
                                client_id, package_id, payment_id,
                                total_hours, used_hours,
                                purchase_date, expiry_date, is_active
                            ) VALUES (%s, %s, %s, %s, 0, %s, %s, 1)
                        """
                        self.db_connection.execute_update(
                            hours_query,
                            (client_id, package_id, payment_id, prepaid_hours, today, end_date)
                        )
                        logger.info(f"Created client_package_hours record: {prepaid_hours} hours for client {client_id}")
                    except Exception as e:
                        logger.error(f"Error creating client_package_hours: {e}")
                        # Don't fail the whole operation, just log the error
                
                self.db_connection.commit()
                logger.info(f"Created payment {payment_id} for package {package_id}")
                
                # Build success message
                success_msg = (
                    f"Η πληρωμή δημιουργήθηκε επιτυχώς!\n\n"
                    f"Πακέτο: {package_name}\n"
                    f"Ποσό: {package_price:.2f} €\n"
                    f"Έναρξη: {today.strftime('%d/%m/%Y')}\n"
                    f"Λήξη: {end_date.strftime('%d/%m/%Y')}"
                )
                
                if prepaid_hours is not None and prepaid_hours > 0:
                    success_msg += f"\n\n✅ Προπληρωμένες Ώρες: {prepaid_hours:.2f} ώρες"
                
                success_msg += "\n\nΜπορείτε να δείτε την πληρωμή στο tab Πληρωμές."
                
                QMessageBox.information(
                    self,
                    "Επιτυχία",
                    success_msg
                )
            else:
                logger.error("Failed to create payment")
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    "Δεν ήταν δυνατή η δημιουργία της πληρωμής.\n"
                    "Μπορείτε να τη δημιουργήσετε χειροκίνητα από το tab Πληρωμές."
                )
                
        except Exception as e:
            logger.error(f"Error creating payment for package: {e}")
            QMessageBox.warning(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά τη δημιουργία πληρωμής: {str(e)}\n\n"
                f"Μπορείτε να τη δημιουργήσετε χειροκίνητα από το tab Πληρωμές."
            )

    def _on_rustdesk_id_changed(self, text: str):
        """Handle RustDesk ID text change - enable/disable connect button."""
        has_id = bool(text.strip())
        self.rustdesk_connect_btn.setEnabled(has_id and self.rustdesk_launcher.is_rustdesk_available())
        
        # Update tooltip
        if not has_id:
            self.rustdesk_connect_btn.setToolTip("Εισάγετε RustDesk ID")
        elif not self.rustdesk_launcher.is_rustdesk_available():
            self.rustdesk_connect_btn.setToolTip("Το RustDesk δεν είναι εγκατεστημένο")
        else:
            self.rustdesk_connect_btn.setToolTip("Σύνδεση μέσω RustDesk")
    
    def _on_rustdesk_connect(self):
        """Handle RustDesk connect button click."""
        rustdesk_id = self.rustdesk_id_input.text().strip()
        if not rustdesk_id:
            QMessageBox.warning(
                self,
                "RustDesk",
                "Παρακαλώ εισάγετε το RustDesk ID του πελάτη"
            )
            return
        
        # Check if RustDesk is available
        if not self.rustdesk_launcher.is_rustdesk_available():
            QMessageBox.warning(
                self,
                "RustDesk",
                "Το RustDesk δεν βρέθηκε στο σύστημα.\n\n"
                "Παρακαλώ εγκαταστήστε το RustDesk από:\n"
                "https://rustdesk.com/download"
            )
            return
        
        # Get password (optional)
        password = self.rustdesk_password_input.text().strip()
        
        # Get client identifier for tracking
        client_tracking_id = f"client_{self.client_id}" if self.client_id else f"temp_{rustdesk_id}"
        
        # Launch RustDesk
        logger.info(f"Launching RustDesk for client: {client_tracking_id}, RustDesk ID: {rustdesk_id}")
        
        success = self.rustdesk_launcher.connect_to_client(
            rustdesk_id=rustdesk_id,
            password=password if password else None,
            client_id=client_tracking_id
        )
        
        if success:
            # Disable connect button while connecting
            self.rustdesk_connect_btn.setEnabled(False)
            self.rustdesk_connect_btn.setText("Συνδέεται...")
        else:
            QMessageBox.warning(
                self,
                "RustDesk",
                "Αποτυχία εκκίνησης RustDesk"
            )
    
    def _on_rustdesk_started(self, client_id: str):
        """Handle RustDesk process started."""
        from datetime import datetime
        
        logger.info(f"RustDesk session started for: {client_id}")
        
        # Record session start time
        self.session_start_time = datetime.now()
        self.active_db_session_id = None
        
        # Create session in database
        if self.db_connection and self.client_id:
            try:
                from services.session_service import SessionService
                svc = SessionService(self.db_connection)
                self.active_db_session_id = svc.start_session(
                    client_id=self.client_id,
                    session_type='remote',
                    description='Απομακρυσμένη υποστήριξη μέσω RustDesk'
                )
                logger.info(f"DB session created: {self.active_db_session_id}")
            except Exception as e:
                logger.error(f"Failed to create DB session: {e}")
        
        # Update button
        self.rustdesk_connect_btn.setText("Συνδεδεμένο")
        self.rustdesk_connect_btn.setStyleSheet("QPushButton{background-color:#1976D2;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#1565C0;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
    
    def _on_rustdesk_finished(self, client_id: str, exit_code: int):
        """Handle RustDesk process finished."""
        from datetime import datetime
        
        logger.info(f"RustDesk session finished for: {client_id}, exit code: {exit_code}")
        
        # End session in database
        if self.active_db_session_id and self.db_connection:
            try:
                from services.session_service import SessionService
                svc = SessionService(self.db_connection)
                success = svc.end_session(
                    self.active_db_session_id,
                    issue_summary='',
                    auto_bill=True
                )
                if success:
                    logger.info(f"DB session {self.active_db_session_id} ended successfully")
                else:
                    logger.error(f"Failed to end DB session {self.active_db_session_id}")
            except Exception as e:
                logger.error(f"Error ending DB session: {e}")
        
        # Calculate session duration for display
        if self.session_start_time:
            session_end_time = datetime.now()
            duration = session_end_time - self.session_start_time
            total_seconds = int(duration.total_seconds())
            duration_minutes = total_seconds // 60
            duration_secs = total_seconds % 60
            
            logger.info(f"Session duration: {duration_minutes}m {duration_secs}s")
            
            QMessageBox.information(
                self,
                "Συνεδρία Ολοκληρώθηκε",
                f"Η συνεδρία RustDesk ολοκληρώθηκε.\n\n"
                f"Διάρκεια: {duration_minutes}λ {duration_secs}δ\n"
                f"Έναρξη: {self.session_start_time.strftime('%H:%M:%S')}\n"
                f"Λήξη: {session_end_time.strftime('%H:%M:%S')}\n\n"
                f"Η συνεδρία αποθηκεύτηκε αυτόματα."
            )
        
        # Reset tracking
        self.session_start_time = None
        self.active_db_session_id = None
        
        # Notify other views that session ended
        self.session_ended.emit()
        
        # Reset button
        self.rustdesk_connect_btn.setText("Connect")
        self.rustdesk_connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.rustdesk_connect_btn.setEnabled(True)
    
    def _on_rustdesk_error(self, client_id: str, error_msg: str):
        """Handle RustDesk process error."""
        logger.error(f"RustDesk error for {client_id}: {error_msg}")
        
        # Show error message
        QMessageBox.critical(
            self,
            "RustDesk Error",
            f"Σφάλμα RustDesk:\n\n{error_msg}"
        )
        
        # Reset button
        self.rustdesk_connect_btn.setText("Connect")
        self.rustdesk_connect_btn.setEnabled(True)
        
        # Reset session tracking
        self.session_start_time = None
    
    def closeEvent(self, event):
        """Handle dialog close event - cleanup RustDesk processes."""
        # Cleanup any active RustDesk processes
        if hasattr(self, 'rustdesk_launcher'):
            self.rustdesk_launcher.cleanup()
        
        super().closeEvent(event)
