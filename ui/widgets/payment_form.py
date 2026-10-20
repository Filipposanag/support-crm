# -*- coding: utf-8 -*-
"""
Payment form dialog for Support CRM.
"""

import logging
from datetime import date, time
from decimal import Decimal
from typing import Optional, Dict, Any
from ui.utils.ui_helpers import gr_question
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QDateEdit, QLineEdit, QDoubleSpinBox,
    QSpinBox, QTextEdit, QDialogButtonBox, QLabel,
    QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, QDate, QEvent, QObject, QSize
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)


class NoWheelFilter(QObject):
    """Event filter to disable mouse wheel on spin boxes and date edits."""
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            return True  # αγνόησε το scroll
        return super().eventFilter(obj, event)


class PaymentForm(QDialog):
    """Dialog for creating and editing payment records."""
    
    def __init__(self, families_repo, payment_data: Optional[Dict[str, Any]] = None, db_connection=None, is_subscription=False, is_renewal=False, parent=None):
        """
        Initialize the payment form.
        
        Args:
            families_repo: FamiliesRepository instance for loading families
            payment_data: Optional payment data for editing
            db_connection: Database connection for auto-numbering service
            is_subscription: True if this is a subscription form (different numbering behavior)
            is_renewal: True if this is a subscription renewal (skip existing subscription check)
            parent: Parent widget
        """
        super().__init__(parent)
        self.families_repo = families_repo
        self.payment_data = payment_data
        # Edit mode only if payment_data has an 'id' field
        self.is_edit_mode = payment_data is not None and payment_data.get('id') is not None
        self.is_subscription = is_subscription
        self.is_renewal = is_renewal
        self.db_connection = db_connection
        
        # Track if user wants to edit existing subscription
        self._existing_subscription_to_edit = None
        
        # Initialize auto-numbering service if db_connection provided
        self.auto_numbering = None
        if db_connection:
            from services.auto_numbering_service import AutoNumberingService
            self.auto_numbering = AutoNumberingService(db_connection)
        
        self.setWindowTitle("Επεξεργασία Πληρωμής" if self.is_edit_mode else "Νέα Πληρωμή")
        
        # Set app icon
        from utils.resource_loader import app_icon
        self.setWindowIcon(app_icon())
        
        # Comfort size for 16:9 screens
        self.setMinimumSize(QSize(900, 550))
        self.resize(900, 550)
        
        # Install no-wheel filter
        self._no_wheel_filter = NoWheelFilter(self)
        
        self._init_ui()
        self._load_families()
        self._setup_family_combobox_placeholder()
        
        if self.is_edit_mode:
            self._populate_form()
        else:
            self._set_defaults()
        
        logger.debug(f"PaymentForm initialized (edit_mode={self.is_edit_mode})")
    
    def _init_ui(self):
        """Initialize the user interface."""
        from PySide6.QtWidgets import QSizePolicy, QScrollArea, QWidget
        
        # Main dialog layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        # Container widget inside scroll area
        scroll_widget = QWidget()
        scroll.setWidget(scroll_widget)
        
        # Container layout
        container_layout = QVBoxLayout(scroll_widget)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(15)
        
        # Form layout with proper spacing
        form = QFormLayout()
        form.setContentsMargins(20, 20, 20, 20)
        form.setHorizontalSpacing(20)
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Helper function to create labels with fixed width
        def create_label(text: str) -> QLabel:
            label = QLabel(text)
            label.setMinimumWidth(140)
            return label
        
        # Helper function to set size policy for input widgets
        def set_input_size_policy(widget):
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Family selector with search button
        family_layout = QHBoxLayout()
        family_layout.setSpacing(8)
        
        self.family_display = QLineEdit()
        self.family_display.setReadOnly(True)
        self.family_display.setPlaceholderText("-- Κάντε κλικ στο κουμπί αναζήτησης --")
        self.family_display.setStyleSheet("background-color: #f9f9f9;")
        set_input_size_policy(self.family_display)
        family_layout.addWidget(self.family_display)
        
        # Search button
        from PySide6.QtWidgets import QPushButton
        self.family_search_btn = QPushButton("Αναζήτηση")
        self.family_search_btn.setToolTip("Αναζήτηση και επιλογή πελάτη")
        self.family_search_btn.setMaximumWidth(120)
        self.family_search_btn.clicked.connect(self._open_family_search)
        family_layout.addWidget(self.family_search_btn)
        
        family_label = create_label("Πελάτης *:")
        form.addRow(family_label, family_layout)
        
        # Store selected family ID
        self.selected_family_id = None
        
        # Receipt number (read-only for subscriptions, editable for payments)
        receipt_layout = QHBoxLayout()
        receipt_layout.setSpacing(8)
        
        self.receipt_no_edit = QLineEdit()
        set_input_size_policy(self.receipt_no_edit)
        
        if self.is_subscription:
            # For subscriptions: read-only, no auto button
            self.receipt_no_edit.setReadOnly(True)
            self.receipt_no_edit.setPlaceholderText("Προαιρετικό")
            self.receipt_no_edit.setStyleSheet("background-color: #f0f0f0;")
        else:
            # For payments: editable with auto button
            self.receipt_no_edit.setPlaceholderText("Αυτόματη αρίθμηση")
            
            # Auto-generate button
            from PySide6.QtWidgets import QPushButton
            self.auto_receipt_btn = QPushButton("Αρίθμηση")
            self.auto_receipt_btn.setToolTip("Δημιουργία αυτόματου αριθμού απόδειξης (Ctrl+G)")
            self.auto_receipt_btn.setMaximumWidth(120)
            self.auto_receipt_btn.clicked.connect(self._generate_receipt_number)
            receipt_layout.addWidget(self.auto_receipt_btn)
            
            # Keyboard shortcut for auto-generate
            from PySide6.QtGui import QShortcut, QKeySequence
            self.auto_shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
            self.auto_shortcut.activated.connect(self._generate_receipt_number)
        
        receipt_layout.addWidget(self.receipt_no_edit)
        receipt_label = create_label("Αριθμός Απόδειξης:")
        form.addRow(receipt_label, receipt_layout)
        
        # Payment date
        self.payment_date_edit = QDateEdit()
        set_input_size_policy(self.payment_date_edit)
        self.payment_date_edit.setCalendarPopup(True)
        self.payment_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.payment_date_edit.setMinimumWidth(130)
        self.payment_date_edit.dateChanged.connect(self._on_date_changed)
        self.payment_date_edit.installEventFilter(self._no_wheel_filter)
        date_label = create_label("Ημερομηνία *:")
        form.addRow(date_label, self.payment_date_edit)
        
        # Description
        self.description_edit = QLineEdit()
        set_input_size_policy(self.description_edit)
        self.description_edit.setPlaceholderText("π.χ. Συνδρομή 2025")
        desc_label = create_label("Περιγραφή:")
        form.addRow(desc_label, self.description_edit)
        
        # Total amount
        self.total_amount_spin = QDoubleSpinBox()
        set_input_size_policy(self.total_amount_spin)
        self.total_amount_spin.setRange(0.0, 999999.99)
        self.total_amount_spin.setDecimals(2)
        self.total_amount_spin.setSuffix(" €")
        self.total_amount_spin.valueChanged.connect(self._calculate_remaining)
        self.total_amount_spin.installEventFilter(self._no_wheel_filter)
        total_label = create_label("Συνολικό Ποσό *:")
        form.addRow(total_label, self.total_amount_spin)
        
        # Paid amount
        self.paid_amount_spin = QDoubleSpinBox()
        set_input_size_policy(self.paid_amount_spin)
        self.paid_amount_spin.setRange(0.0, 999999.99)
        self.paid_amount_spin.setDecimals(2)
        self.paid_amount_spin.setSuffix(" €")
        self.paid_amount_spin.valueChanged.connect(self._calculate_remaining)
        self.paid_amount_spin.installEventFilter(self._no_wheel_filter)
        paid_label = create_label("Πληρωμένο Ποσό *:")
        form.addRow(paid_label, self.paid_amount_spin)
        
        # Remaining amount (calculated, read-only)
        self.remaining_label = QLabel("0.00 €")
        remaining_font = QFont()
        remaining_font.setBold(True)
        self.remaining_label.setFont(remaining_font)
        remaining_label_text = create_label("Υπόλοιπο:")
        form.addRow(remaining_label_text, self.remaining_label)
        
        # Support Package selector
        support_package_layout = QHBoxLayout()
        support_package_layout.setSpacing(8)
        
        self.support_package_combo = QComboBox()
        self.support_package_combo.addItem("-- Χωρίς Πακέτο --", None)
        # Packages will be loaded from database
        self._load_support_packages()
        self.support_package_combo.setMinimumWidth(200)
        self.support_package_combo.setToolTip(
            "Επιλέξτε πακέτο υποστήριξης. Το πακέτο θα ενημερωθεί αυτόματα στον πελάτη."
        )
        self.support_package_combo.currentIndexChanged.connect(self._on_package_selected)
        set_input_size_policy(self.support_package_combo)
        support_package_layout.addWidget(self.support_package_combo)
        
        support_package_label = create_label("Πακέτο Υποστήριξης:")
        form.addRow(support_package_label, support_package_layout)
        
        # Subscription checkbox
        self.subscription_checkbox = QCheckBox("Αφορά συνδρομή")
        self.subscription_checkbox.setToolTip(
            "Αν η απόδειξη αφορά πληρωμή συνδρομής, "
            "δημιουργήστε αυτόματα συνδρομή για τον πελάτη."
        )
        self.subscription_checkbox.stateChanged.connect(self._on_subscription_checkbox_changed)
        form.addRow("", self.subscription_checkbox)
        
        # Subscription code (shown when checkbox is checked) - READ-ONLY
        subscription_layout = QHBoxLayout()
        subscription_layout.setSpacing(8)
        
        self.subscription_code_edit = QLineEdit()
        set_input_size_policy(self.subscription_code_edit)
        self.subscription_code_edit.setReadOnly(True)  # Read-only field
        self.subscription_code_edit.setPlaceholderText("Αυτόματη αρίθμηση (π.χ. ΣΥΝ-2025-001)")
        self.subscription_code_edit.setStyleSheet("background-color: #f0f0f0;")  # Visual indication
        subscription_layout.addWidget(self.subscription_code_edit)
        
        # Auto-generate button for subscription
        from PySide6.QtWidgets import QPushButton
        self.auto_subscription_btn = QPushButton("Αρίθμηση")
        self.auto_subscription_btn.setToolTip("Δημιουργία αυτόματου αριθμού συνδρομής")
        self.auto_subscription_btn.setMaximumWidth(120)
        self.auto_subscription_btn.clicked.connect(self._generate_subscription_number)
        subscription_layout.addWidget(self.auto_subscription_btn)
        
        self.subscription_code_label = create_label("Αριθμός Συνδρομής:")
        form.addRow(self.subscription_code_label, subscription_layout)
        
        # Initially hide subscription code fields
        self.subscription_code_label.setVisible(False)
        self.subscription_code_edit.setVisible(False)
        self.auto_subscription_btn.setVisible(False)
        
        # Bank payment checkbox (unlocks subscription start date)
        self.bank_payment_checkbox = QCheckBox("Αφορά Τραπεζική πληρωμή")
        self.bank_payment_checkbox.setToolTip(
            "Αν είναι επιλεγμένο, μπορείτε να αλλάξετε την ημερομηνία έναρξης συνδρομής\n"
            "(για πληρωμές που έγιναν σε προηγούμενη ημερομηνία μέσω τράπεζας)"
        )
        self.bank_payment_checkbox.stateChanged.connect(self._on_bank_payment_changed)
        self.bank_payment_checkbox.setVisible(False)  # Initially hidden
        form.addRow("", self.bank_payment_checkbox)
        
        # Subscription start date (read-only by default, editable when bank payment is checked)
        self.subscription_start_edit = QDateEdit()
        set_input_size_policy(self.subscription_start_edit)
        self.subscription_start_edit.setCalendarPopup(True)
        self.subscription_start_edit.setDisplayFormat("dd/MM/yyyy")
        self.subscription_start_edit.setMinimumWidth(130)
        self.subscription_start_edit.setDate(QDate.currentDate())
        self.subscription_start_edit.setReadOnly(True)
        self.subscription_start_edit.setStyleSheet("background-color: #f0f0f0;")
        self.subscription_start_edit.installEventFilter(self._no_wheel_filter)
        self.subscription_start_label = create_label("Έναρξη Συνδρομής:")
        form.addRow(self.subscription_start_label, self.subscription_start_edit)
        
        # Subscription end date
        self.subscription_end_edit = QDateEdit()
        set_input_size_policy(self.subscription_end_edit)
        self.subscription_end_edit.setCalendarPopup(True)
        self.subscription_end_edit.setDisplayFormat("dd/MM/yyyy")
        self.subscription_end_edit.setMinimumWidth(130)
        self.subscription_end_edit.installEventFilter(self._no_wheel_filter)
        self.subscription_end_label = create_label("Λήξη Συνδρομής:")
        form.addRow(self.subscription_end_label, self.subscription_end_edit)
        
        # Initially hide subscription date fields
        self.subscription_start_label.setVisible(False)
        self.subscription_start_edit.setVisible(False)
        self.subscription_end_label.setVisible(False)
        self.subscription_end_edit.setVisible(False)
        
        # Remarks
        self.remarks_edit = QTextEdit()
        self.remarks_edit.setMaximumHeight(80)
        self.remarks_edit.setMinimumHeight(60)
        self.remarks_edit.setPlaceholderText("Προαιρετικές σημειώσεις...")
        remarks_label = create_label("Παρατηρήσεις:")
        form.addRow(remarks_label, self.remarks_edit)
        
        # Add form to container layout
        container_layout.addLayout(form)
        
        # Add stretch to push form to top
        container_layout.addStretch()
        
        # Required fields note
        note_label = QLabel("* Υποχρεωτικά πεδία")
        note_label.setStyleSheet("color: #666; font-size: 11px; font-style: italic;")
        container_layout.addWidget(note_label)
        
        # Add scroll area to main layout
        layout.addWidget(scroll)
        
        # Fix Qt6 indicator refresh for spinboxes and date edits
        for widget in [self.payment_date_edit, self.total_amount_spin, self.paid_amount_spin]:
            widget.setStyle(widget.style())
        
        # Add spacing before buttons
        layout.addSpacing(10)
        
        # Dialog buttons - aligned right with same width
        from PySide6.QtWidgets import QPushButton
        self.ok_button = QPushButton("OK")
        self.ok_button.setMinimumWidth(90)
        self.ok_button.clicked.connect(self._on_accept)
        
        self.cancel_button = QPushButton("Ακύρωση")
        self.cancel_button.setMinimumWidth(90)
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addSpacing(20)  # Add spacing on the right
        
        layout.addLayout(buttons_layout)
        layout.addSpacing(10)  # Add spacing at the bottom
    
    def _load_families(self):
        """No longer needed - families are loaded in the search dialog."""
        pass
    
    def _load_support_packages(self):
        """Load support packages from database."""
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
                
                # Store package data as tuple: (id, type, price)
                self.support_package_combo.addItem(
                    display_text,
                    (package_id, pkg_type, price)
                )
            
            logger.debug(f"Loaded {len(packages)} support packages")
            
        except Exception as e:
            logger.error(f"Error loading support packages: {e}")
    
    def _on_package_selected(self, index):
        """Handle package selection - auto-fill price."""
        if index <= 0:  # "Χωρίς Πακέτο" selected
            return
        
        package_data = self.support_package_combo.currentData()
        if package_data and len(package_data) == 3:
            package_id, pkg_type, price = package_data
            
            # Auto-fill total amount if it's currently 0
            if self.total_amount_spin.value() == 0:
                self.total_amount_spin.setValue(price)
                logger.debug(f"Auto-filled price: {price} from package")
    
    def _setup_family_combobox_placeholder(self):
        """No longer needed - using search dialog instead."""
        pass
    
    def _open_family_search(self):
        """Open the family search dialog."""
        from ui.dialogs.family_search_dialog import FamilySearchDialog
        
        dialog = FamilySearchDialog(self.families_repo, self)
        
        if dialog.exec() == QDialog.Accepted:
            family_id, family_name = dialog.get_selected_family()
            if family_id:
                self.selected_family_id = family_id
                self.family_display.setText(family_name)
                logger.info(f"Family selected: {family_name} (ID: {family_id})")
    
    def _set_defaults(self):
        """Set default values for new payment."""
        logger.debug(f"_set_defaults called: is_subscription={self.is_subscription}, is_edit_mode={self.is_edit_mode}, has_auto_numbering={self.auto_numbering is not None}")
        
        # Set today's date
        self.payment_date_edit.setDate(QDate.currentDate())
        
        # Set family if provided in payment_data (for renewals)
        if self.payment_data:
            family_id = self.payment_data.get('family_id')
            if family_id:
                self.selected_family_id = family_id
                # Load family name from repo
                try:
                    family = self.families_repo.get_family_by_id(family_id)
                    if family:
                        family_name = f"{family.get('last_name', '')} {family.get('first_name', '')}".strip()
                        self.family_display.setText(family_name)
                        logger.debug(f"Pre-selected family_id={family_id}")
                except Exception as e:
                    logger.error(f"Error loading family: {e}")
        
        # Set default amounts or from payment_data
        if self.payment_data:
            total_amount = self.payment_data.get('total_amount', 0)
            if isinstance(total_amount, Decimal):
                total_amount = float(total_amount)
            self.total_amount_spin.setValue(total_amount)
            
            # Set description if provided
            description = self.payment_data.get('description', '')
            if description:
                self.description_edit.setText(description)
        else:
            self.total_amount_spin.setValue(0.0)
        
        self.paid_amount_spin.setValue(0.0)
        
        # Subscription start date is always today (read-only)
        self.subscription_start_edit.setDate(QDate.currentDate())
        
        # Set subscription end date if provided in payment_data
        if self.payment_data:
            sub_end = self.payment_data.get('subscription_end_date')
            if sub_end:
                if isinstance(sub_end, str):
                    from datetime import datetime
                    try:
                        sub_end = datetime.strptime(sub_end, '%Y-%m-%d').date()
                    except:
                        sub_end = None
                if sub_end:
                    qdate = QDate(sub_end.year, sub_end.month, sub_end.day)
                    self.subscription_end_edit.setDate(qdate)
                else:
                    # Default to 1 year from today
                    today = date.today()
                    one_year_later = date(today.year + 1, today.month, today.day)
                    self.subscription_end_edit.setDate(QDate(one_year_later.year, one_year_later.month, one_year_later.day))
            else:
                # Default to 1 year from today
                today = date.today()
                one_year_later = date(today.year + 1, today.month, today.day)
                self.subscription_end_edit.setDate(QDate(one_year_later.year, one_year_later.month, one_year_later.day))
        else:
            # Default to 1 year from today
            today = date.today()
            one_year_later = date(today.year + 1, today.month, today.day)
            self.subscription_end_edit.setDate(QDate(one_year_later.year, one_year_later.month, one_year_later.day))
        
        # If this is a subscription form, check the subscription checkbox by default
        if self.is_subscription:
            self.subscription_checkbox.setChecked(True)
            logger.debug("Subscription checkbox checked (is_subscription=True)")
        # Or if payment_data has subscription dates
        elif self.payment_data and (
            self.payment_data.get('subscription_start_date') is not None or
            self.payment_data.get('subscription_end_date') is not None
        ):
            self.subscription_checkbox.setChecked(True)
            logger.debug("Subscription checkbox checked (has subscription dates)")
        
        # Auto-generate receipt number for new records (subscription number is auto-generated when checkbox is checked)
        if not self.is_edit_mode and self.auto_numbering and not self.is_subscription:
            # For payments: auto-generate receipt number
            logger.info("Auto-generating receipt number...")
            self._generate_receipt_number()
        else:
            logger.debug(f"Skipping auto-generation: is_edit_mode={self.is_edit_mode}, has_auto_numbering={self.auto_numbering is not None}")
    
    def _populate_form(self):
        """Populate form with existing payment data."""
        if not self.payment_data:
            return
        
        # Set family
        family_id = self.payment_data.get('family_id')
        if family_id:
            self.selected_family_id = family_id
            # Load family name from repo
            try:
                family = self.families_repo.get_family_by_id(family_id)
                if family:
                    family_name = f"{family.get('last_name', '')} {family.get('first_name', '')}".strip()
                    self.family_display.setText(family_name)
            except Exception as e:
                logger.error(f"Error loading family: {e}")
        
        # Set payment date
        payment_date = self.payment_data.get('payment_date')
        if payment_date:
            if isinstance(payment_date, str):
                # Parse string date
                from datetime import datetime
                try:
                    payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
                except:
                    payment_date = date.today()
            qdate = QDate(payment_date.year, payment_date.month, payment_date.day)
            self.payment_date_edit.setDate(qdate)
        
        # Set description
        self.description_edit.setText(self.payment_data.get('description', ''))
        
        # Set amounts
        total_amount = self.payment_data.get('total_amount', 0)
        if isinstance(total_amount, Decimal):
            total_amount = float(total_amount)
        self.total_amount_spin.setValue(total_amount)
        
        paid_amount = self.payment_data.get('paid_amount', 0)
        if isinstance(paid_amount, Decimal):
            paid_amount = float(paid_amount)
        self.paid_amount_spin.setValue(paid_amount)
        
        # Set subscription start date (if editing, keep existing; otherwise today)
        sub_start = self.payment_data.get('subscription_start_date')
        if sub_start:
            if isinstance(sub_start, str):
                from datetime import datetime
                try:
                    sub_start = datetime.strptime(sub_start, '%Y-%m-%d').date()
                except:
                    sub_start = None
            if sub_start:
                qdate = QDate(sub_start.year, sub_start.month, sub_start.day)
                self.subscription_start_edit.setDate(qdate)
        
        # Set subscription end date
        sub_end = self.payment_data.get('subscription_end_date')
        if sub_end:
            if isinstance(sub_end, str):
                from datetime import datetime
                try:
                    sub_end = datetime.strptime(sub_end, '%Y-%m-%d').date()
                except:
                    sub_end = None
            if sub_end:
                qdate = QDate(sub_end.year, sub_end.month, sub_end.day)
                self.subscription_end_edit.setDate(qdate)
        
        # Set receipt number
        self.receipt_no_edit.setText(self.payment_data.get('receipt_no', ''))
        
        # Set support package if exists
        if hasattr(self, 'support_package_combo'):
            support_package = self.payment_data.get('support_package')
            if support_package:
                # Find the package by type
                for i in range(self.support_package_combo.count()):
                    package_data = self.support_package_combo.itemData(i)
                    if package_data and len(package_data) == 3:
                        package_id, pkg_type, price = package_data
                        if pkg_type == support_package:
                            self.support_package_combo.setCurrentIndex(i)
                            break
        
        # Set subscription code (if exists)
        if hasattr(self, 'subscription_code_edit'):
            subscription_code = self.payment_data.get('subscription_code', '')
            self.subscription_code_edit.setText(subscription_code)
            # Show fields if there's a subscription code
            if subscription_code:
                if hasattr(self, 'subscription_code_label'):
                    self.subscription_code_label.setVisible(True)
                self.subscription_code_edit.setVisible(True)
                if hasattr(self, 'auto_subscription_btn'):
                    self.auto_subscription_btn.setVisible(True)
        
        # Set remarks
        self.remarks_edit.setPlainText(self.payment_data.get('remarks', ''))
        
        # Check if this payment has subscription dates set
        has_subscription = (
            self.payment_data.get('subscription_start_date') is not None and
            self.payment_data.get('subscription_end_date') is not None
        )
        
        # Set subscription checkbox
        if has_subscription:
            self.subscription_checkbox.setChecked(True)
            # Optionally disable checkbox if subscription already exists
            # self.subscription_checkbox.setEnabled(False)
            self.subscription_checkbox.setToolTip(
                "Αυτή η πληρωμή είναι ήδη συνδεδεμένη με συνδρομή."
            )
        
        # Check if this is a free subscription (description contains "Δωρεάν" or end_date is 2099)
        # Calculate remaining
        self._calculate_remaining()
    
    def _on_date_changed(self, qdate: QDate):
        """Handle date change - update subscription end date to +1 year."""
        # Update subscription end date to exactly 1 year from payment date
        payment_date = qdate.toPython()
        
        # Handle leap year edge case (Feb 29 -> Feb 28 next year)
        try:
            one_year_later = date(payment_date.year + 1, payment_date.month, payment_date.day)
        except ValueError:
            # If day is out of range (e.g., Feb 29 in non-leap year), use last day of month
            if payment_date.month == 2 and payment_date.day == 29:
                one_year_later = date(payment_date.year + 1, 2, 28)
            else:
                # Fallback: use the last day of the month
                import calendar
                last_day = calendar.monthrange(payment_date.year + 1, payment_date.month)[1]
                one_year_later = date(payment_date.year + 1, payment_date.month, last_day)
        
        self.subscription_end_edit.setDate(QDate(one_year_later.year, one_year_later.month, one_year_later.day))
    
    def _calculate_remaining(self):
        """Calculate and display remaining amount."""
        total = Decimal(str(self.total_amount_spin.value()))
        paid = Decimal(str(self.paid_amount_spin.value()))
        remaining = total - paid
        
        self.remaining_label.setText(f"{remaining:.2f} €")
        
        # Color code the remaining amount
        if remaining <= 0:
            self.remaining_label.setStyleSheet("color: green; font-weight: bold;")
        elif remaining > 0 and paid > 0:
            self.remaining_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.remaining_label.setStyleSheet("color: red; font-weight: bold;")
    
    def _on_subscription_checkbox_changed(self, state):
        """Handle subscription checkbox state change."""
        is_checked = state == Qt.CheckState.Checked.value
        
        # Show/hide subscription code fields
        if hasattr(self, 'subscription_code_label'):
            self.subscription_code_label.setVisible(is_checked)
        if hasattr(self, 'subscription_code_edit'):
            self.subscription_code_edit.setVisible(is_checked)
        if hasattr(self, 'auto_subscription_btn'):
            self.auto_subscription_btn.setVisible(is_checked)
        
        # Show/hide subscription date fields
        if hasattr(self, 'subscription_start_label'):
            self.subscription_start_label.setVisible(is_checked)
        if hasattr(self, 'subscription_start_edit'):
            self.subscription_start_edit.setVisible(is_checked)
        
        # Check if family is association member to pre-check free subscription
        is_association_member = self._check_if_association_member()
        
        # Show/hide bank payment checkbox
        if hasattr(self, 'bank_payment_checkbox'):
            self.bank_payment_checkbox.setVisible(is_checked)
            if not is_checked:
                self.bank_payment_checkbox.setChecked(False)
        
        # Show/hide end date
        if hasattr(self, 'subscription_end_label'):
            self.subscription_end_label.setVisible(is_checked)
        if hasattr(self, 'subscription_end_edit'):
            self.subscription_end_edit.setVisible(is_checked)
        
        if is_checked:
            # When checked, auto-generate subscription number if empty and not in edit mode
            if not self.is_edit_mode and self.auto_numbering:
                if hasattr(self, 'subscription_code_edit'):
                    current_value = self.subscription_code_edit.text().strip()
                    if not current_value:
                        logger.info("Auto-generating subscription number on checkbox check...")
                        self._generate_subscription_number()
            
            logger.debug("Subscription checkbox checked - keeping existing dates")
        else:
            # When unchecked, optionally clear subscription code
            # (commented out to preserve user data)
            # if hasattr(self, 'subscription_code_edit'):
            #     self.subscription_code_edit.clear()
            pass
    
    def _check_if_association_member(self) -> bool:
        """Check if the selected family is an association member."""
        if not self.selected_family_id:
            return False
        try:
            family = self.families_repo.get_family_by_id(self.selected_family_id)
            if family:
                return family.get('is_association_member', False)
        except Exception as e:
            logger.error(f"Error checking association member status: {e}")
        return False
    
    def _on_bank_payment_changed(self, state):
        """Handle bank payment checkbox state change."""
        is_bank_payment = state == Qt.CheckState.Checked.value
        
        # Enable/disable subscription start date editing
        self.subscription_start_edit.setReadOnly(not is_bank_payment)
        if is_bank_payment:
            self.subscription_start_edit.setStyleSheet("")  # Remove gray background
            self.subscription_start_edit.setToolTip("Επιλέξτε την ημερομηνία της τραπεζικής πληρωμής")
        else:
            self.subscription_start_edit.setStyleSheet("background-color: #f0f0f0;")
            self.subscription_start_edit.setDate(QDate.currentDate())  # Reset to today
            self.subscription_start_edit.setToolTip("")
    
    def _generate_receipt_number(self):
        """Generate automatic receipt number."""
        if not self.auto_numbering:
            QMessageBox.information(
                self,
                "Πληροφορία",
                "Η αυτόματη αρίθμηση δεν είναι διαθέσιμη.\n"
                "Παρακαλώ εισάγετε αριθμό χειροκίνητα."
            )
            return
        
        try:
            # Disable button during generation
            self.auto_receipt_btn.setEnabled(False)
            self.auto_receipt_btn.setText("Δημιουργία...")
            
            # Generate receipt number
            receipt_no = self.auto_numbering.get_next_receipt_number()
            
            # Check if it's an error code
            if receipt_no.startswith('ERROR-'):
                raise Exception("Αποτυχία δημιουργίας αριθμού από το service")
            
            # The auto_numbering service now automatically syncs with the database
            # and finds the next available number, so no need for manual checking
            
            # Set the receipt number
            self.receipt_no_edit.setText(receipt_no)
            
            # Visual feedback - green background briefly
            self.receipt_no_edit.setStyleSheet("background-color: #E8F5E9;")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, lambda: self.receipt_no_edit.setStyleSheet(""))
            
            logger.info(f"Generated receipt number: {receipt_no}")
            
        except Exception as e:
            logger.error(f"Failed to generate receipt number: {e}")
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                f"Αποτυχία αυτόματης αρίθμησης.\n\n"
                f"Παρακαλώ εισάγετε αριθμό χειροκίνητα.\n\n"
                f"Σφάλμα: {str(e)}"
            )
            self.receipt_no_edit.setFocus()
        
        finally:
            # Re-enable button
            if not self.is_subscription:
                self.auto_receipt_btn.setEnabled(True)
                self.auto_receipt_btn.setText("Αρίθμηση")
    
    def _generate_subscription_number(self):
        """Generate automatic subscription number."""
        logger.debug("_generate_subscription_number called")
        
        # Check if subscription_code_edit exists
        if not hasattr(self, 'subscription_code_edit'):
            logger.warning("subscription_code_edit not found, skipping auto-generation")
            return
        
        logger.debug("subscription_code_edit exists, proceeding...")
        
        if not self.auto_numbering:
            QMessageBox.information(
                self,
                "Πληροφορία",
                "Η αυτόματη αρίθμηση δεν είναι διαθέσιμη.\n"
                "Παρακαλώ εισάγετε αριθμό χειροκίνητα."
            )
            return
        
        try:
            # Disable button during generation (if it exists)
            if hasattr(self, 'auto_subscription_btn'):
                self.auto_subscription_btn.setEnabled(False)
                self.auto_subscription_btn.setText("Δημιουργία...")
            
            # Generate subscription number
            subscription_no = self.auto_numbering.get_next_subscription_number()
            
            # Check if it's an error code
            if subscription_no.startswith('ERROR-'):
                raise Exception("Αποτυχία δημιουργίας αριθμού από το service")
            
            # Set the subscription number
            self.subscription_code_edit.setText(subscription_no)
            
            # Visual feedback - green background briefly
            self.subscription_code_edit.setStyleSheet("background-color: #E8F5E9;")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, lambda: self.subscription_code_edit.setStyleSheet(""))
            
            logger.info(f"Generated subscription number: {subscription_no}")
            
        except Exception as e:
            logger.error(f"Failed to generate subscription number: {e}")
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                f"Αποτυχία αυτόματης αρίθμησης.\n\n"
                f"Παρακαλώ εισάγετε αριθμό χειροκίνητα.\n\n"
                f"Σφάλμα: {str(e)}"
            )
            if hasattr(self, 'subscription_code_edit'):
                self.subscription_code_edit.setFocus()
        
        finally:
            # Re-enable button (if it exists)
            if hasattr(self, 'auto_subscription_btn'):
                self.auto_subscription_btn.setEnabled(True)
                self.auto_subscription_btn.setText("Αρίθμηση")
    
    def _validate(self) -> bool:
        """Validate form data."""
        errors = []
        
        # Validate family selection
        if self.selected_family_id is None:
            errors.append("Παρακαλώ επιλέξτε πελάτη")
        
        # Validate amounts
        if self.total_amount_spin.value() < 0:
            errors.append("Το συνολικό ποσό δεν μπορεί να είναι αρνητικό")
        
        if self.paid_amount_spin.value() < 0:
            errors.append("Το πληρωμένο ποσό δεν μπορεί να είναι αρνητικό")
        
        # Check if zero subscription is allowed (only when free subscription checkbox is checked)
        # Check for existing active subscription if creating new subscription
        # Skip this check for renewals - renewals should always create new subscriptions
        if self.subscription_checkbox.isChecked() and self.selected_family_id and not self.is_renewal:
            # Get subscription year from start date
            sub_start_qdate = self.subscription_start_edit.date()
            subscription_year = sub_start_qdate.year()
            
            # Check if subscription already exists for this family and year
            # Only check if NOT in edit mode, or if in edit mode but changing the family
            should_check = True
            if self.is_edit_mode and self.payment_data:
                original_family_id = self.payment_data.get('family_id')
                original_year = self.payment_data.get('year')
                # Don't check if editing same family and same year
                if original_family_id == self.selected_family_id and original_year == subscription_year:
                    should_check = False
            
            if should_check and self.db_connection:
                try:
                    from db.repositories.subscriptions_repo import SubscriptionsRepository
                    subscriptions_repo = SubscriptionsRepository(self.db_connection)
                    
                    existing_sub = subscriptions_repo.get_by_family_and_year(
                        self.selected_family_id, 
                        subscription_year
                    )
                    
                    if existing_sub:
                        # Get family name for better message
                        family_name = self.family_display.text()
                        
                        # Show informative message with option to edit
                        reply = gr_question(
                            self,
                            "Υπάρχει ήδη Συνδρομή",
                            f"Ο πελάτης '{family_name}' έχει ήδη συνδρομή για το έτος {subscription_year}.\n\n"
                            f"Ημερομηνία λήξης: {existing_sub.get('end_date')}\n"
                            f"Κατάσταση: {existing_sub.get('status')}\n\n"
                            "Δεν μπορείτε να δημιουργήσετε δεύτερη συνδρομή για τον ίδιο πελάτη και έτος.\n\n"
                            "Θέλετε να επεξεργαστείτε την υπάρχουσα συνδρομή;",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No
                        )
                        
                        if reply == QMessageBox.Yes:
                            # User wants to edit - close this dialog and signal to open edit
                            self._existing_subscription_to_edit = existing_sub
                            self.reject()  # Close current dialog
                        
                        return False
                        
                except Exception as e:
                    logger.error(f"Error checking for existing subscription: {e}")
                    # Continue with validation even if check fails
        
        if errors:
            QMessageBox.warning(
                self,
                "Σφάλμα Επικύρωσης",
                "\n".join(errors)
            )
            return False
        
        return True
    
    def _on_accept(self):
        """Handle OK button click."""
        if self._validate():
            # If free subscription is checked, update family as association member
            if hasattr(self, 'free_subscription_checkbox') and self.free_subscription_checkbox.isChecked():
                self._update_family_association_member(True)
            self.accept()
    
    def _update_family_association_member(self, is_member: bool):
        """Update family's association member status."""
        if not self.selected_family_id:
            return
        
        try:
            # Check current status
            family = self.families_repo.get_family_by_id(self.selected_family_id)
            if family:
                current_status = family.get('is_association_member', False)
                if current_status != is_member:
                    # Update family
                    self.families_repo.update_family(
                        self.selected_family_id, 
                        {'is_association_member': 1 if is_member else 0}
                    )
                    if self.db_connection:
                        self.db_connection.commit()
                    logger.info(f"Updated family {self.selected_family_id} is_association_member={is_member}")
        except Exception as e:
            logger.error(f"Error updating family association member status: {e}")
    
    def get_payment_data(self) -> Dict[str, Any]:
        """Get the payment data from the form."""
        # Get payment date
        qdate = self.payment_date_edit.date()
        payment_date = date(qdate.year(), qdate.month(), qdate.day())
        
        # Calculate amounts
        total_amount = Decimal(str(self.total_amount_spin.value()))
        paid_amount = Decimal(str(self.paid_amount_spin.value()))
        remaining_amount = total_amount - paid_amount
        
        # Calculate status
        if remaining_amount <= 0:
            status = 'PAID'
        elif paid_amount > 0:
            status = 'PARTIAL'
        else:
            status = 'UNPAID'
        
        # Get subscription dates based on checkbox
        subscription_start_date = None
        subscription_end_date = None
        subscription_year = None
        is_free_subscription = False
        
        # Only set subscription dates if checkbox is checked
        if self.subscription_checkbox.isChecked():
            sub_start_qdate = self.subscription_start_edit.date()
            subscription_start_date = date(sub_start_qdate.year(), sub_start_qdate.month(), sub_start_qdate.day())
            
            # Use the selected end date
            sub_end_qdate = self.subscription_end_edit.date()
            subscription_end_date = date(sub_end_qdate.year(), sub_end_qdate.month(), sub_end_qdate.day())
            
            # Calculate year from subscription start date
            subscription_year = subscription_start_date.year
            
            # Note: Subscription dates are saved and subscription will be created regardless of payment status
            logger.debug(f"Subscription checkbox is checked - dates saved, subscription will be created (payment status: {status})")
            
            # Auto-generate subscription code if not already set
            if hasattr(self, 'subscription_code_edit'):
                subscription_code = self.subscription_code_edit.text().strip()
                if not subscription_code and self.auto_numbering:
                    logger.info("Auto-generating subscription code before save...")
                    try:
                        subscription_code = self.auto_numbering.get_next_subscription_number()
                        if not subscription_code.startswith('ERROR-'):
                            self.subscription_code_edit.setText(subscription_code)
                            logger.info(f"Generated subscription code: {subscription_code}")
                    except Exception as e:
                        logger.error(f"Failed to auto-generate subscription code: {e}")
        
        data = {
            'family_id': self.selected_family_id,
            'payment_date': payment_date,
            'payment_time': None,  # Not currently used
            'description': self.description_edit.text().strip(),
            'receipt_no': self.receipt_no_edit.text().strip(),
            'remarks': self.remarks_edit.toPlainText().strip(),
            'total_amount': total_amount,
            'paid_amount': paid_amount,
            'remaining_amount': remaining_amount,
            'status': status,
            'year': subscription_year if subscription_year else payment_date.year,
            'subscription_start_date': subscription_start_date,
            'subscription_end_date': subscription_end_date,
        }
        
        # Add subscription_code if field exists (even if empty)
        if hasattr(self, 'subscription_code_edit'):
            subscription_code = self.subscription_code_edit.text().strip()
            data['subscription_code'] = subscription_code if subscription_code else None
        
        # Add support_package if field exists
        if hasattr(self, 'support_package_combo'):
            package_data = self.support_package_combo.currentData()
            if package_data and len(package_data) == 3:
                package_id, pkg_type, price = package_data
                # Store the package type (for backward compatibility)
                data['support_package'] = pkg_type
            else:
                data['support_package'] = None
        
        # Include ID if editing
        if self.is_edit_mode and self.payment_data:
            data['id'] = self.payment_data.get('id')
        
        return data
    
    def get_existing_subscription_to_edit(self) -> Optional[Dict[str, Any]]:
        """
        Get the existing subscription that user wants to edit (if any).
        
        Returns:
            Subscription dictionary or None
        """
        return self._existing_subscription_to_edit
