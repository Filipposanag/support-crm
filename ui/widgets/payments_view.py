# -*- coding: utf-8 -*-
"""
Payments view for Support CRM.
"""

import logging
from datetime import date
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QPushButton, QComboBox, QLineEdit, QCheckBox,
    QLabel, QMessageBox, QHeaderView, QAbstractItemView,
    QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon

from ui.widgets.payments_table_model import PaymentsTableModel
from ui.widgets.payment_form import PaymentForm
from ui.utils.ui_helpers import style_payments_table, gr_question
from ui.utils.permission_helper import has_permission
from db.repositories.subscriptions_repo import SubscriptionsRepository

logger = logging.getLogger(__name__)


class PaymentsView(QWidget):
    """View for managing payment records."""
    
    # Signal emitted when payment data changes (create, update, delete)
    payment_changed = Signal()
    
    def __init__(self, payments_repo, families_repo, receipt_service=None, settings_service=None, db_connection=None, parent=None):
        """
        Initialize the payments view.
        
        Args:
            payments_repo: PaymentsRepository instance
            families_repo: FamiliesRepository instance
            receipt_service: ReceiptService instance (optional)
            settings_service: SettingsService instance (optional)
            db_connection: Database connection for auto-numbering (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        self.payments_repo = payments_repo
        self.families_repo = families_repo
        self.receipt_service = receipt_service
        self.settings_service = settings_service
        self.db_connection = db_connection
        
        # Initialize subscriptions repository
        if db_connection:
            self.subscriptions_repo = SubscriptionsRepository(db_connection)
        else:
            self.subscriptions_repo = None
            logger.warning("SubscriptionsRepository not initialized - db_connection is None")
        
        # State
        self.current_page = 0
        self.page_size = 50
        self.total_count = 0
        
        # Debounce timer for search
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        
        self._init_ui()
        self._load_data()
        
        # Apply column preferences after initial load
        if self.settings_service:
            QTimer.singleShot(100, self.apply_column_preferences)
        
        logger.debug("PaymentsView initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel("Διαχείριση Πληρωμών")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Filter bar
        filter_layout = QHBoxLayout()
        
        # Year filter
        filter_layout.addWidget(QLabel("Έτος:"))
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(120)
        self._populate_year_combo()
        self.year_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.year_combo)
        
        # Client search
        filter_layout.addWidget(QLabel("Πελάτης:"))
        self.family_search_edit = QLineEdit()
        self.family_search_edit.setPlaceholderText("Κωδικός, επώνυμο, όνομα...")
        self.family_search_edit.setMinimumWidth(200)
        self.family_search_edit.textChanged.connect(self._on_search_changed)
        filter_layout.addWidget(self.family_search_edit)
        
        # Search preferences button
        from resources.icons import get_icon
        self.search_prefs_btn = QPushButton(get_icon('settings'), "Προτιμήσεις Αναζήτησης")
        self.search_prefs_btn.clicked.connect(self._show_search_preferences)
        filter_layout.addWidget(self.search_prefs_btn)
        
        # Only with debt checkbox
        self.only_debt_checkbox = QCheckBox("Μόνο με οφειλή")
        self.only_debt_checkbox.stateChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.only_debt_checkbox)
        
        # Only with package checkbox
        self.only_package_checkbox = QCheckBox("Μόνο με πακέτο")
        self.only_package_checkbox.stateChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.only_package_checkbox)
        
        # Refresh button
        self.refresh_btn = QPushButton("Ανανέωση")
        self.refresh_btn.clicked.connect(self._load_data)
        filter_layout.addWidget(self.refresh_btn)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Table view
        self.table_view = QTableView()
        self.table_model = PaymentsTableModel(self)
        self.table_view.setModel(self.table_model)
        
        # Table settings
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Note: setSortingEnabled will be called after loading data
        
        # Enable multi-selection (Ctrl+A, Ctrl+Click)
        from ui.utils.ui_helpers import enable_multi_selection
        enable_multi_selection(self.table_view)
        
        # Apply consistent table styling
        style_payments_table(self.table_view)
        
        # Status column uses full cell background color from model (BackgroundRole)
        
        # Make sure last column stretches to fill space
        self.table_view.horizontalHeader().setStretchLastSection(True)
        
        # Double-click to edit
        self.table_view.doubleClicked.connect(self._on_edit_payment)
        
        layout.addWidget(self.table_view, stretch=1)
        
        # Pagination info
        self.pagination_label = QLabel()
        self.pagination_label.setStyleSheet("color: #666;")
        layout.addWidget(self.pagination_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        
        self.edit_btn = QPushButton(get_icon('edit'), "Επεξεργασία")
        self.edit_btn.clicked.connect(self._on_edit_payment)
        self.edit_btn.setEnabled(False)
        self.edit_btn.setStyleSheet("QPushButton{background-color:#F9A825;color:#212121;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#F57F17;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton(get_icon('delete'), "Διαγραφή")
        self.delete_btn.clicked.connect(self._on_delete_payment)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("QPushButton{background-color:#E53935;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#C62828;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        button_layout.addWidget(self.delete_btn)
        
        
        button_layout.addSpacing(20)
        
        self.receipt_btn = QPushButton("Έκδοση Απόδειξης (PDF)")
        self.receipt_btn.clicked.connect(self._on_generate_receipt)
        self.receipt_btn.setEnabled(False)
        self.receipt_btn.setStyleSheet("QPushButton{background-color:#1976D2;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#1565C0;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        button_layout.addWidget(self.receipt_btn)
        
        button_layout.addStretch()
        
        # Pagination buttons
        self.prev_btn = QPushButton("Προηγούμενη")
        self.prev_btn.clicked.connect(self._on_previous_page)
        self.prev_btn.setEnabled(False)
        button_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("Επόμενη")
        self.next_btn.clicked.connect(self._on_next_page)
        self.next_btn.setEnabled(False)
        button_layout.addWidget(self.next_btn)
        
        layout.addLayout(button_layout)
        
        # Connect selection changed
        self.table_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )
    
    def _populate_year_combo(self):
        """Populate the year combo box."""
        current_year = date.today().year
        
        self.year_combo.addItem("Όλα", None)
        self.year_combo.addItem(str(current_year), current_year)
        self.year_combo.addItem(str(current_year - 1), current_year - 1)
        self.year_combo.addItem(str(current_year - 2), current_year - 2)
        
        # Add more years if needed
        for i in range(3, 10):
            year = current_year - i
            self.year_combo.addItem(str(year), year)
    
    def _on_filter_changed(self):
        """Handle filter change."""
        self.current_page = 0
        self._load_data()
    
    def _on_search_changed(self):
        """Handle search text change with debounce."""
        self.search_timer.stop()
        self.search_timer.start(500)  # 500ms debounce
    
    def _perform_search(self):
        """Perform the actual search."""
        self.current_page = 0
        self._load_data()
    
    def _load_data(self):
        """Load payment data from repository."""
        try:
            # Get filter values
            year = self.year_combo.currentData()
            only_debt = self.only_debt_checkbox.isChecked()
            only_package = self.only_package_checkbox.isChecked()
            family_search = self.family_search_edit.text().strip()
            
            # Get search fields from settings
            search_fields = None
            if self.settings_service:
                settings = self.settings_service.get_all_settings()
                if settings:
                    search_fields = settings.get_search_fields("payments")
            
            # Get family_id if searching by family
            family_id = None
            if family_search:
                # Search for family using search fields
                families = self.families_repo.list_families(
                    search=family_search,
                    only_active=True,
                    limit=1,
                    offset=0,
                    search_fields=search_fields
                )
                if families:
                    family_id = families[0].get('id')
            
            # If "only with package" is checked, filter by support_package
            if only_package:
                # Get payments with support_package
                query = """
                    SELECT p.*, 
                           f.legacy_code as family_code,
                           CONCAT(f.last_name, ' ', f.first_name) as family_name
                    FROM payments p
                    INNER JOIN families f ON p.family_id = f.id
                    WHERE p.support_package IS NOT NULL
                    AND p.support_package != ''
                """
                
                params = []
                
                if year:
                    query += " AND p.year = %s"
                    params.append(year)
                
                if family_id:
                    query += " AND p.family_id = %s"
                    params.append(family_id)
                
                if only_debt:
                    query += " AND p.remaining_amount > 0"
                
                query += " ORDER BY p.payment_date DESC LIMIT %s OFFSET %s"
                params.extend([self.page_size, self.current_page * self.page_size])
                
                payments = self.payments_repo.db.execute_query(query, tuple(params) if params else None)
                
                # Count query
                count_query = """
                    SELECT COUNT(*) as count
                    FROM payments p
                    WHERE p.support_package IS NOT NULL
                    AND p.support_package != ''
                """
                
                count_params = []
                
                if year:
                    count_query += " AND p.year = %s"
                    count_params.append(year)
                
                if family_id:
                    count_query += " AND p.family_id = %s"
                    count_params.append(family_id)
                
                if only_debt:
                    count_query += " AND p.remaining_amount > 0"
                
                count_result = self.payments_repo.db.execute_query(count_query, tuple(count_params) if count_params else None)
                self.total_count = count_result[0]['count'] if count_result else 0
            else:
                # Normal query without package filter
                # Get total count
                self.total_count = self.payments_repo.count_payments(
                    year=year,
                    family_id=family_id,
                    only_with_debt=only_debt
                )
                
                # Get payments
                payments = self.payments_repo.list_payments(
                    year=year,
                    family_id=family_id,
                    only_with_debt=only_debt,
                    limit=self.page_size,
                    offset=self.current_page * self.page_size
                )
            
            # Update table
            self.table_model.set_payments(payments)
            
            # Enable sorting and apply default sort
            self.table_view.setSortingEnabled(False)  # Disable temporarily
            self.table_view.sortByColumn(2, Qt.DescendingOrder)  # Sort by payment date
            self.table_view.setSortingEnabled(True)  # Enable for user interaction
            
            # Reapply table styling after model update
            style_payments_table(self.table_view)
            
            # Update pagination
            self._update_pagination()
            
            logger.info(f"Loaded {len(payments)} payments (total: {self.total_count})")
        
        except Exception as e:
            logger.error(f"Error loading payments: {e}")
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Αποτυχία φόρτωσης πληρωμών: {str(e)}"
            )
    
    def refresh(self):
        """
        Refresh the payments view.
        Public method that can be called from other views.
        """
        logger.debug("Refreshing payments view")
        self._load_data()
    
    def _update_pagination(self):
        """Update pagination controls and label."""
        total_pages = (self.total_count + self.page_size - 1) // self.page_size
        current_page_display = self.current_page + 1 if self.total_count > 0 else 0
        
        self.pagination_label.setText(
            f"Σελίδα {current_page_display} από {total_pages} "
            f"(Σύνολο: {self.total_count} πληρωμές)"
        )
        
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled((self.current_page + 1) * self.page_size < self.total_count)
    
    def _on_previous_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._load_data()
    
    def _on_next_page(self):
        """Go to next page."""
        if (self.current_page + 1) * self.page_size < self.total_count:
            self.current_page += 1
            self._load_data()
    
    def _on_selection_changed(self):
        """Handle table selection change."""
        has_selection = len(self.table_view.selectionModel().selectedRows()) > 0
        self.edit_btn.setEnabled(has_selection and has_permission('payments.edit'))
        self.delete_btn.setEnabled(has_selection and has_permission('payments.delete'))
        self.receipt_btn.setEnabled(has_selection and has_permission('payments.create'))
    
    def _get_selected_payment(self) -> Optional[dict]:
        """Get the currently selected payment."""
        selection = self.table_view.selectionModel().selectedRows()
        if not selection:
            return None
        
        row = selection[0].row()
        return self.table_model.get_payment_at_row(row)
    
    def _on_new_payment(self):
        """Handle new payment button click."""
        dialog = PaymentForm(self.families_repo, db_connection=self.db_connection, parent=self)
        
        result = dialog.exec_()
        
        # Check if user wants to edit existing subscription instead
        existing_sub = dialog.get_existing_subscription_to_edit()
        if existing_sub:
            # User chose to edit existing subscription
            # Find the payment associated with this subscription
            payment_id = existing_sub.get('payment_id')
            if payment_id:
                try:
                    payment = self.payments_repo.get_by_id(payment_id)
                    if payment:
                        # Open edit dialog for the existing payment
                        self._edit_payment_by_data(payment)
                        return
                except Exception as e:
                    logger.error(f"Error loading existing payment: {e}")
                    QMessageBox.warning(
                        self,
                        "Σφάλμα",
                        f"Δεν ήταν δυνατή η φόρτωση της υπάρχουσας πληρωμής:\n{str(e)}"
                    )
            return
        
        if result:
            try:
                payment_data = dialog.get_payment_data()
                payment_id = self.payments_repo.create_payment(payment_data)
                
                # Commit the transaction to save to database
                self.payments_repo.db.commit()
                
                logger.info(f"Created payment with id={payment_id}")
                
                # Check if subscription was created
                has_subscription = (
                    payment_data.get('subscription_start_date') is not None and
                    payment_data.get('subscription_end_date') is not None
                )
                
                # Note: Subscription is already created inside payments_repo.create_payment()
                # No need to call create_subscription_from_payment again here
                subscription_id = None
                if has_subscription:
                    logger.debug(f"Subscription was created automatically for payment {payment_id}")
                
                # Reload data first
                self._load_data()
                
                # Emit signal to refresh other views (e.g., subscriptions)
                self.payment_changed.emit()
                
                # Build success message
                success_message = "Η πληρωμή δημιουργήθηκε επιτυχώς!"
                if has_subscription:
                    success_message += "\n\n✓ Η συνδρομή δημιουργήθηκε αυτόματα."
                    success_message += f"\nΈναρξη: {payment_data['subscription_start_date'].strftime('%d/%m/%Y')}"
                    success_message += f"\nΛήξη: {payment_data['subscription_end_date'].strftime('%d/%m/%Y')}"
                    if subscription_id:
                        success_message += f"\n(Subscription ID: {subscription_id})"
                
                success_message += "\n\nΘέλετε να εκδώσετε απόδειξη PDF;"
                
                # Ask user if they want to generate PDF receipt
                reply = gr_question(
                    self,
                    "Επιτυχία",
                    success_message,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self._generate_receipt_for_payment(payment_id, payment_data)
            
            except Exception as e:
                logger.error(f"Error creating payment: {e}")
                # Rollback on error
                self.payments_repo.db.rollback()
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    f"Αποτυχία δημιουργίας πληρωμής: {str(e)}"
                )
    
    def _on_edit_payment(self):
        """Handle edit payment button click."""
        if not has_permission('payments.edit'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα επεξεργασίας πληρωμών.")
            return
        payment = self._get_selected_payment()
        if not payment:
            return
        
        self._edit_payment_by_data(payment)
    
    def _edit_payment_by_data(self, payment: dict):
        """
        Edit a payment given its data dictionary.
        Helper method to allow editing from different contexts.
        
        Args:
            payment: Payment data dictionary
        """
        dialog = PaymentForm(self.families_repo, payment_data=payment, db_connection=self.db_connection, parent=self)
        
        if dialog.exec_():
            try:
                payment_data = dialog.get_payment_data()
                payment_id = payment.get('id')
                
                success = self.payments_repo.update_payment(payment_id, payment_data)
                
                # Commit the transaction to save to database
                self.payments_repo.db.commit()
                
                if success:
                    logger.info(f"Updated payment id={payment_id}")
                    
                    # Check if subscription was added/updated
                    has_subscription = (
                        payment_data.get('subscription_start_date') is not None and
                        payment_data.get('subscription_end_date') is not None
                    )
                    
                    # Update or create subscription in subscriptions table if needed
                    subscription_id = None
                    if has_subscription and self.subscriptions_repo:
                        try:
                            # Get the updated payment
                            updated_payment = self.payments_repo.get_by_id(payment_id)
                            
                            # Check if subscription already exists (regardless of payment status)
                            family_id = updated_payment.get('family_id')
                            year = updated_payment.get('year')
                            existing_sub = self.subscriptions_repo.get_by_family_and_year(family_id, year)
                            
                            if existing_sub:
                                # Update existing subscription
                                logger.info(f"Subscription already exists for family {family_id}, year {year}")
                                subscription_id = existing_sub.get('id')
                            else:
                                # Create new subscription (even if payment is UNPAID)
                                subscription_id = self.subscriptions_repo.create_subscription_from_payment(updated_payment)
                                logger.info(f"Created subscription {subscription_id} from updated payment {payment_id} (status: {updated_payment.get('status')})")
                        except Exception as sub_error:
                            logger.error(f"Failed to update/create subscription: {sub_error}")
                            # Don't fail the whole operation
                    
                    # Build success message
                    success_message = "Η πληρωμή ενημερώθηκε επιτυχώς"
                    if has_subscription:
                        success_message += "\n\n✓ Η συνδρομή ενημερώθηκε."
                        success_message += f"\nΈναρξη: {payment_data['subscription_start_date'].strftime('%d/%m/%Y')}"
                        success_message += f"\nΛήξη: {payment_data['subscription_end_date'].strftime('%d/%m/%Y')}"
                        if subscription_id:
                            success_message += f"\n(Subscription ID: {subscription_id})"
                    
                    QMessageBox.information(
                        self,
                        "Επιτυχία",
                        success_message
                    )
                    self._load_data()
                    
                    # Emit signal to refresh other views
                    self.payment_changed.emit()
                else:
                    QMessageBox.warning(
                        self,
                        "Προειδοποίηση",
                        "Δεν βρέθηκε η πληρωμή για ενημέρωση"
                    )
            
            except Exception as e:
                logger.error(f"Error updating payment: {e}")
                # Rollback on error
                self.payments_repo.db.rollback()
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    f"Αποτυχία ενημέρωσης πληρωμής: {str(e)}"
                )
    
    def _on_delete_payment(self):
        """Handle delete payment button click (supports multiple selection)."""
        if not has_permission('payments.delete'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα διαγραφής πληρωμών.")
            return
        # Get all selected payment IDs
        selected_indexes = self.table_view.selectionModel().selectedRows()
        
        if not selected_indexes:
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Παρακαλώ επιλέξτε τουλάχιστον μία πληρωμή"
            )
            return
        
        # Get payment IDs from selected rows
        payment_ids = []
        for index in selected_indexes:
            row = index.row()
            payment = self.table_model.get_payment_at_row(row)
            if payment and payment.get('id'):
                payment_ids.append(payment.get('id'))
        
        if not payment_ids:
            return
        
        # Check if any payment has active subscription
        payments_with_active_subs = []
        if self.subscriptions_repo:
            try:
                for payment_id in payment_ids:
                    check_query = """
                        SELECT s.id, s.status, s.end_date, p.id as payment_id,
                               CONCAT(f.last_name, ' ', f.first_name) as family_name
                        FROM subscriptions s
                        JOIN payments p ON s.payment_id = p.id
                        JOIN families f ON p.family_id = f.id
                        WHERE s.payment_id = %s
                        AND s.status = 'ACTIVE'
                        AND s.end_date >= CURDATE()
                    """
                    active_subs = self.subscriptions_repo.db.execute_query(check_query, (payment_id,))
                    
                    if active_subs and len(active_subs) > 0:
                        payments_with_active_subs.append(active_subs[0])
                
                if payments_with_active_subs:
                    payment_list = "\n".join([
                        f"• {sub['family_name']} (λήγει {sub['end_date'].strftime('%d/%m/%Y')})"
                        for sub in payments_with_active_subs
                    ])
                    QMessageBox.warning(
                        self,
                        "Αδυναμία Διαγραφής",
                        f"Δεν μπορείτε να διαγράψετε {len(payments_with_active_subs)} πληρωμή/ές!\n\n"
                        f"Οι παρακάτω πληρωμές έχουν ενεργές συνδρομές:\n\n"
                        f"{payment_list}\n\n"
                        f"Για να διαγράψετε αυτές τις πληρωμές, πρέπει πρώτα να ακυρώσετε\n"
                        f"τις συνδρομές από το tab 'Συνδρομές'."
                    )
                    return
            except Exception as e:
                logger.error(f"Error checking for active subscriptions: {e}")
        
        # Confirm deletion
        count = len(payment_ids)
        reply = gr_question(
            self,
            "Επιβεβαίωση Διαγραφής",
            f"Είστε σίγουροι ότι θέλετε να διαγράψετε {count} πληρωμή/ές;\n\n"
            f"Αυτή η ενέργεια δεν μπορεί να αναιρεθεί.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success_count = 0
            failed_count = 0
            
            try:
                for payment_id in payment_ids:
                    try:
                        success = self.payments_repo.delete_payment(payment_id)
                        if success:
                            success_count += 1
                            logger.info(f"Deleted payment id={payment_id}")
                        else:
                            failed_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting payment {payment_id}: {e}")
                        failed_count += 1
                
                # Show result
                if success_count > 0:
                    message = f"Διαγράφηκαν επιτυχώς {success_count} πληρωμή/ές"
                    if failed_count > 0:
                        message += f"\n\nΑπέτυχαν {failed_count} διαγραφές"
                    
                    QMessageBox.information(
                        self,
                        "Επιτυχία",
                        message
                    )
                    
                    self._load_data()
                    self.payment_changed.emit()
                else:
                    QMessageBox.warning(
                        self,
                        "Προειδοποίηση",
                        f"Απέτυχαν όλες οι διαγραφές ({failed_count})"
                    )
            
            except Exception as e:
                logger.error(f"Error in bulk delete: {e}")
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    f"Αποτυχία διαγραφής πληρωμών: {str(e)}"
                )
    
    def _on_generate_receipt(self):
        """Έκδοση παραστατικού (Απόδειξη ή Τιμολόγιο) για την επιλεγμένη πληρωμή."""
        payment = self._get_selected_payment()
        if not payment:
            return
        payment_id = payment.get('id')
        if not payment_id:
            return
        try:
            from ui.widgets.document_type_dialog import issue_document_from_db
            issue_document_from_db(
                self, payment_id, self.payments_repo.db,
                clients_repo=getattr(self, 'clients_repo', None),
                client_name=payment.get('family_name', ''),
            )
        except Exception as e:
            logger.error(f"Issue document failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία έκδοσης παραστατικού:\n{e}")

    def _on_manage_packages(self):
        """Handle manage packages button click."""
        from ui.dialogs.support_packages_dialog import SupportPackagesDialog
        
        if not self.db_connection:
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Η σύνδεση με τη βάση δεδομένων δεν είναι διαθέσιμη"
            )
            return
        
        dialog = SupportPackagesDialog(self.db_connection, parent=self)
        dialog.packages_changed.connect(self._on_packages_changed)
        dialog.exec()
    
    def _on_packages_changed(self):
        """Handle packages changed signal."""
        logger.info("Support packages were modified")
        # Optionally refresh payment form dropdowns if needed
    
    def _on_send_receipt_email(self):
        """Handle send receipt email button click."""
        payment = self._get_selected_payment()
        if not payment:
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Επιλέξτε πρώτα μία πληρωμή."
            )
            return
        
        # Get family email
        family_id = payment.get('family_id')
        if not family_id:
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Δεν βρέθηκε ο πελάτης για αυτή την πληρωμή."
            )
            return
        
        try:
            family = self.families_repo.get_by_id(family_id)
            if not family or not family.get('email'):
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    "Ο πελάτης δεν έχει email. Παρακαλώ προσθέστε email στα στοιχεία του πελάτη."
                )
                return
            
            # Prepare payment data for email
            payment_data = {
                'family_name': payment.get('family_name', ''),
                'payment_date': str(payment.get('date', '')),
                'amount': f"{payment.get('total_amount', 0):.2f}",
                'receipt_no': payment.get('receipt_no', '')
            }
            
            # Generate PDF if receipt service is available
            pdf_path = None
            if self.receipt_service:
                try:
                    import tempfile
                    import os
                    
                    # Create temp PDF
                    temp_dir = tempfile.gettempdir()
                    pdf_filename = f"receipt_{payment.get('id')}_{payment.get('family_name', 'family')}.pdf"
                    pdf_path = os.path.join(temp_dir, pdf_filename)
                    
                    self.receipt_service.generate_document_pdf(payment.get('id'), pdf_path, (payment.get('document_type') or 'receipt'))
                    logger.info(f"Temporary receipt PDF generated: {pdf_path}")
                    
                except Exception as e:
                    logger.warning(f"Failed to generate PDF for email: {e}")
                    pdf_path = None
            
            # Show email dialog
            from ui.widgets.send_receipt_email_dialog import SendReceiptEmailDialog
            from services.email_service import EmailService
            
            email_service = EmailService(self.settings_service)
            
            dialog = SendReceiptEmailDialog(
                email_service,
                self.settings_service,
                family.get('email'),
                payment_data,
                pdf_path,
                self
            )
            dialog.exec()
            
            # Clean up temp PDF if created
            if pdf_path:
                try:
                    import os
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                        logger.debug(f"Temporary PDF removed: {pdf_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary PDF: {e}")
            
        except Exception as e:
            logger.error(f"Error sending receipt email: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά την αποστολή email:\n\n{str(e)}"
            )
    
    def _on_open_family(self):
        """Handle open family button click - open family form directly."""
        payment = self._get_selected_payment()
        if not payment:
            return
        
        family_id = payment.get('family_id')
        if not family_id:
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Δεν βρέθηκε ο πελάτης για αυτή την πληρωμή."
            )
            return
        
        try:
            # Open client form directly
            from ui.widgets.client_form import ClientForm
            from ui.i18n import TranslationManager
            
            tr_manager = TranslationManager()
            
            dialog = ClientForm(
                clients_repo=self.families_repo,
                tr_manager=tr_manager,
                client_id=family_id,
                parent=self
            )
            
            if dialog.exec():
                # Refresh payments view if client was updated
                self._load_data()
                
        except Exception as e:
            logger.error(f"Error opening client form: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά το άνοιγμα του πελάτη:\n\n{str(e)}"
            )
    
    def _generate_receipt_for_payment(self, payment_id: int, payment_data: dict):
        """
        Generate PDF receipt for a newly created payment.
        
        Args:
            payment_id: ID of the payment
            payment_data: Payment data dictionary
        """
        # Check if receipt service is available
        if not self.receipt_service:
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Η υπηρεσία έκδοσης αποδείξεων δεν είναι διαθέσιμη."
            )
            logger.warning("Receipt service not available")
            return
        
        # Get family name for filename
        family_id = payment_data.get('family_id')
        family_name = 'family'
        
        if family_id:
            try:
                families = self.families_repo.list_families(
                    search='',
                    only_active=False,
                    limit=1,
                    offset=0
                )
                # Find the family by ID
                for fam in families:
                    if fam.get('id') == family_id:
                        family_name = f"{fam.get('last_name', '')} {fam.get('first_name', '')}".strip()
                        break
            except:
                pass
        
        # Clean family name for filename
        safe_family_name = "".join(c for c in family_name if c.isalnum() or c in (' ', '_')).strip()
        safe_family_name = safe_family_name.replace(' ', '_')
        
        # Default filename
        default_filename = f"receipt_{payment_id}_{safe_family_name}.pdf"
        
        # Open file save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Αποθήκευση Απόδειξης",
            default_filename,
            "PDF Files (*.pdf)"
        )
        
        if not file_path:
            return  # User cancelled
        
        # Ensure .pdf extension
        if not file_path.lower().endswith('.pdf'):
            file_path += '.pdf'
        
        try:
            # Generate PDF
            self.receipt_service.generate_document_pdf(payment_id, file_path, (payment_data.get('document_type') or 'receipt'))
            
            logger.info(f"Receipt PDF generated: {file_path}")
            
            # Ask if user wants to open the PDF
            reply = gr_question(
                self,
                "Επιτυχία",
                f"Η απόδειξη δημιουργήθηκε επιτυχώς!\n\n"
                f"Αποθηκεύτηκε στο:\n{file_path}\n\n"
                f"Θέλετε να ανοίξετε το PDF;",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                import os
                os.startfile(file_path)
        
        except ValueError as e:
            # Validation error - show detailed message
            error_msg = str(e)
            logger.error(f"Validation error: {error_msg}")
            QMessageBox.critical(
                self,
                "Σφάλμα Δεδομένων",
                f"{error_msg}\n\n"
                f"Παρακαλώ ελέγξτε τα στοιχεία της πληρωμής και τις ρυθμίσεις του οργανισμού."
            )
        
        except Exception as e:
            # General error
            error_msg = str(e)
            logger.error(f"Error generating receipt: {error_msg}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Αποτυχία δημιουργίας απόδειξης:\n\n{error_msg}\n\n"
                f"Ελέγξτε το αρχείο καταγραφής για περισσότερες λεπτομέρειες."
            )

    def apply_column_preferences(self):
        """Apply column visibility and lock preferences from settings."""
        if not self.settings_service:
            return
        
        try:
            # Load settings
            settings = self.settings_service.get_all_settings()
            if not settings:
                return
            
            # Get visible columns and lock status
            visible_columns = settings.get_visible_columns("payments")
            locked = settings.get_columns_locked("payments")
            
            # Column mapping: internal key -> column index
            from ui.widgets.payments_table_model import PaymentsTableModel
            column_map = {
                "date": 0,
                "family_code": 1,
                "family_name": 2,
                "description": 3,
                "subscription_start_date": 4,
                "subscription_end_date": 5,
                "total_amount": 6,
                "paid_amount": 7,
                "remaining_amount": 8,
                "status": 9,
                "receipt_no": 10,
            }
            
            # Apply column visibility
            for key, col_index in column_map.items():
                # ALWAYS show family_name column (client must always be visible)
                if key == "family_name":
                    self.table_view.setColumnHidden(col_index, False)
                else:
                    self.table_view.setColumnHidden(col_index, key not in visible_columns)
            
            # Apply column lock
            header = self.table_view.horizontalHeader()
            
            # Always ensure last column stretches to fill space
            header.setStretchLastSection(True)
            
            if locked:
                # Lock all columns except the last one
                for col_index in range(self.table_model.columnCount()):
                    if col_index < self.table_model.columnCount() - 1:
                        header.setSectionResizeMode(col_index, QHeaderView.Fixed)
                    else:
                        header.setSectionResizeMode(col_index, QHeaderView.Stretch)
            else:
                # All columns interactive, last one stretches
                for col_index in range(self.table_model.columnCount()):
                    if col_index < self.table_model.columnCount() - 1:
                        header.setSectionResizeMode(col_index, QHeaderView.Interactive)
                    else:
                        header.setSectionResizeMode(col_index, QHeaderView.Stretch)
            
            logger.debug(f"Applied column preferences for payments view (locked={locked})")
        
        except Exception as e:
            logger.error(f"Error applying column preferences: {e}", exc_info=True)

    def _show_search_preferences(self):
        """Show search preferences dialog."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox, QLabel, QGroupBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Προτιμήσεις Αναζήτησης")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Title
        title = QLabel("Επιλέξτε τα πεδία που θέλετε να αναζητούνται:")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Group box for search fields
        group = QGroupBox("Πεδία Αναζήτησης")
        group_layout = QVBoxLayout()
        
        # Get current preferences from settings
        if self.settings_service:
            settings = self.settings_service.get_all_settings()
            search_fields = settings.get_search_fields("payments") if settings else []
        else:
            search_fields = ["receipt_number", "description"]  # defaults
        
        # Create checkboxes for each field
        self.search_field_checkboxes = {}
        
        fields = [
            ("code", "Κωδικός Πελάτη"),
            ("last_name", "Επώνυμο"),
            ("first_name", "Όνομα"),
            ("phone", "Τηλέφωνο"),
            ("receipt_number", "Αριθμός Απόδειξης"),
            ("description", "Περιγραφή"),
        ]
        
        for field_key, field_label in fields:
            checkbox = QCheckBox(field_label)
            checkbox.setChecked(field_key in search_fields)
            self.search_field_checkboxes[field_key] = checkbox
            group_layout.addWidget(checkbox)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self._save_search_preferences(dialog, "payments"))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.exec()
    
    def _save_search_preferences(self, dialog, view_name):
        """Save search preferences to settings."""
        if not self.settings_service:
            dialog.accept()
            return
        
        try:
            # Get selected fields
            selected_fields = [
                field_key for field_key, checkbox in self.search_field_checkboxes.items()
                if checkbox.isChecked()
            ]
            
            # Save to settings (via Settings object)
            settings = self.settings_service.get_all_settings()
            if settings:
                settings.set_search_fields(view_name, selected_fields)
                # Save to database
                self.settings_service.save_settings(settings)
            
            logger.info(f"Search preferences saved for {view_name}: {selected_fields}")
            dialog.accept()
        except Exception as e:
            logger.error(f"Error saving search preferences: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Αποτυχία αποθήκευσης προτιμήσεων:\n{str(e)}"
            )
