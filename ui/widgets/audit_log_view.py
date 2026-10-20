# -*- coding: utf-8 -*-
"""
Audit Log View - Display audit trail of database changes.
"""

import logging
import json
from typing import Optional
from datetime import datetime, date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QLabel, QComboBox, QDateEdit, QMessageBox, QHeaderView,
    QAbstractItemView
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QDate
from PySide6.QtGui import QColor
from ui.utils.ui_helpers import gr_question

from db.repositories.audit_log_repo import AuditLogRepository

logger = logging.getLogger(__name__)


class AuditLogTableModel(QAbstractTableModel):
    """Table model for audit log data."""
    
    COLUMNS = [
        ('ID', 'id'),
        ('Πίνακας', 'table_name'),
        ('Record ID', 'record_id'),
        ('Ενέργεια', 'operation'),
        ('Χρήστης', 'changed_by'),
        ('Ημερομηνία', 'changed_at'),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
    
    def rowCount(self, parent=QModelIndex()):
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        
        if row >= len(self._data):
            return None
        
        record = self._data[row]
        col_key = self.COLUMNS[col][1]
        
        if role == Qt.DisplayRole:
            value = record.get(col_key)
            
            # Format datetime
            if col_key == 'changed_at' and isinstance(value, datetime):
                return value.strftime('%d/%m/%Y %H:%M:%S')
            
            # Translate operation
            if col_key == 'operation':
                translations = {
                    'INSERT': 'Προσθήκη',
                    'UPDATE': 'Τροποποίηση',
                    'DELETE': 'Διαγραφή'
                }
                return translations.get(value, value)
            
            # Translate table name
            if col_key == 'table_name':
                translations = {
                    'families': 'Πελάτες',
                    'payments': 'Πληρωμές',
                    'subscriptions': 'Συνδρομές',
                    'members': 'Μέλη'
                }
                return translations.get(value, value)
            
            return str(value) if value is not None else ''
        
        elif role == Qt.BackgroundRole:
            # Color code by operation
            operation = record.get('operation')
            if operation == 'INSERT':
                return QColor('#E8F5E9')  # Light green
            elif operation == 'UPDATE':
                return QColor('#FFF3E0')  # Light orange
            elif operation == 'DELETE':
                return QColor('#FFEBEE')  # Light red
        
        elif role == Qt.TextAlignmentRole:
            if col_key in ['id', 'record_id']:
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter
        
        elif role == Qt.UserRole:
            # Store full record for details view
            return record
        
        return None
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if section < len(self.COLUMNS):
                return self.COLUMNS[section][0]
        return None
    
    def set_data(self, data):
        """Update model data."""
        self.beginResetModel()
        self._data = data
        self.endResetModel()
    
    def get_record(self, row: int):
        """Get full record at row."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None


class AuditLogView(QWidget):
    """View for displaying audit log."""
    
    def __init__(self, audit_log_repo: AuditLogRepository, parent=None):
        super().__init__(parent)
        self.audit_log_repo = audit_log_repo
        
        # Pagination settings
        self.page_size = 50  # 50 records per page
        self.current_page = 0
        self.total_records = 0
        
        # Auto-cleanup: enforce 1000 record limit
        self._enforce_record_limit()
        
        self._init_ui()
        self._load_data()
    
    def _enforce_record_limit(self):
        """Enforce maximum 1000 audit log records."""
        try:
            deleted = self.audit_log_repo.enforce_limit(max_records=1000)
            if deleted > 0:
                logger.info(f"Auto-cleanup: deleted {deleted} old audit log records")
        except Exception as e:
            logger.error(f"Error enforcing audit log limit: {e}")
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Ιστορικό Κινήσεων (Audit Log)")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1976D2;")
        layout.addWidget(title_label)
        
        # Filters
        filter_layout = QHBoxLayout()
        
        # Table filter
        filter_layout.addWidget(QLabel("Πίνακας:"))
        self.table_combo = QComboBox()
        self.table_combo.addItem("Όλοι", "")
        self.table_combo.addItem("Πελάτες", "families")
        self.table_combo.addItem("Πληρωμές", "payments")
        self.table_combo.addItem("Συνδρομές", "subscriptions")
        self.table_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.table_combo)
        
        filter_layout.addSpacing(20)
        
        # Date range filter
        filter_layout.addWidget(QLabel("Από:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.start_date_edit.dateChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.start_date_edit)
        
        filter_layout.addWidget(QLabel("Έως:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.dateChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.end_date_edit)
        
        filter_layout.addStretch()
        
        # Clear audit log button
        clear_btn = QPushButton("Καθαρισμός Ιστορικού")
        clear_btn.setStyleSheet("background-color: #F44336; color: white;")
        clear_btn.clicked.connect(self._clear_audit_log)
        filter_layout.addWidget(clear_btn)
        
        # Export to Excel button
        from resources.icons import get_icon
        export_btn = QPushButton(get_icon('excel'), "Εξαγωγή σε Excel")
        export_btn.clicked.connect(self._export_to_excel)
        filter_layout.addWidget(export_btn)
        
        # Refresh button
        refresh_btn = QPushButton("Ανανέωση")
        refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(refresh_btn)
        
        layout.addLayout(filter_layout)
        
        # Table
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(False)
        
        # Enable multi-selection (Ctrl+A, Ctrl+Click)
        from ui.utils.ui_helpers import enable_multi_selection
        enable_multi_selection(self.table_view)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Set up model
        self.model = AuditLogTableModel(self)
        self.table_view.setModel(self.model)
        
        # Configure columns
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Table
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Record ID
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Operation
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # User
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Date
        
        # Double-click to show details
        self.table_view.doubleClicked.connect(self._show_details)
        
        layout.addWidget(self.table_view)
        
        # Pagination controls - Exact layout from image
        from PySide6.QtWidgets import QSpinBox, QApplication, QStyle
        
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(8)
        
        # Left side - Records per page with spinbox
        pagination_layout.addWidget(QLabel("Γραμμές ανά σελίδα:"))
        
        self.page_size_spinbox = QSpinBox()
        self.page_size_spinbox.setMinimum(10)
        self.page_size_spinbox.setMaximum(200)
        self.page_size_spinbox.setSingleStep(10)
        self.page_size_spinbox.setValue(self.page_size)
        self.page_size_spinbox.setMinimumWidth(70)
        self.page_size_spinbox.setMaximumWidth(90)
        self.page_size_spinbox.valueChanged.connect(self._on_page_size_changed)
        pagination_layout.addWidget(self.page_size_spinbox)
        
        pagination_layout.addSpacing(20)
        
        # Get system style for standard icons
        style = QApplication.style()
        
        # Navigation buttons with system icons
        self.first_page_btn = QPushButton(
            style.standardIcon(QStyle.SP_MediaSkipBackward),
            "Πρώτη"
        )
        self.first_page_btn.clicked.connect(self._go_to_first_page)
        pagination_layout.addWidget(self.first_page_btn)
        
        self.prev_page_btn = QPushButton(
            style.standardIcon(QStyle.SP_ArrowBack),
            "Προηγούμενη"
        )
        self.prev_page_btn.clicked.connect(self._go_to_prev_page)
        pagination_layout.addWidget(self.prev_page_btn)
        
        # Page info label
        self.page_label = QLabel()
        self.page_label.setMinimumWidth(150)
        self.page_label.setAlignment(Qt.AlignCenter)
        pagination_layout.addWidget(self.page_label)
        
        self.next_page_btn = QPushButton(
            style.standardIcon(QStyle.SP_ArrowForward),
            "Επόμενη"
        )
        self.next_page_btn.clicked.connect(self._go_to_next_page)
        pagination_layout.addWidget(self.next_page_btn)
        
        self.last_page_btn = QPushButton(
            style.standardIcon(QStyle.SP_MediaSkipForward),
            "Τελευταία"
        )
        self.last_page_btn.clicked.connect(self._go_to_last_page)
        pagination_layout.addWidget(self.last_page_btn)
        
        pagination_layout.addStretch()
        
        # Right side - Status label
        self.status_label = QLabel()
        pagination_layout.addWidget(self.status_label)
        
        layout.addLayout(pagination_layout)
    
    def _on_page_size_changed(self, value: int):
        """Handle page size change."""
        self.page_size = value
        self.current_page = 0  # Reset to first page
        self._load_data()
    
    def _load_data(self):
        """Load audit log data based on current filters and pagination."""
        try:
            # Get filter values
            table_name = self.table_combo.currentData()
            start_date = self.start_date_edit.date().toPython()
            end_date = self.end_date_edit.date().toPython()
            
            # Calculate offset
            offset = self.current_page * self.page_size
            
            # Fetch data with pagination
            if table_name:
                # Filter by table and date range
                all_logs = self.audit_log_repo.get_logs_by_table(table_name, limit=5000)
                # Apply date filter
                filtered_logs = [log for log in all_logs 
                               if start_date <= log['changed_at'].date() <= end_date]
                self.total_records = len(filtered_logs)
                # Apply pagination
                logs = filtered_logs[offset:offset + self.page_size]
            else:
                # Filter by date range only
                all_logs = self.audit_log_repo.get_logs_by_date_range(start_date, end_date, limit=5000)
                self.total_records = len(all_logs)
                # Apply pagination
                logs = all_logs[offset:offset + self.page_size]
            
            # Update model
            self.model.set_data(logs)
            
            # Update pagination UI
            self._update_pagination_ui()
            
            logger.info(f"Loaded {len(logs)} audit log records (page {self.current_page + 1})")
            
        except Exception as e:
            logger.error(f"Error loading audit log data: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά τη φόρτωση δεδομένων:\n{str(e)}"
            )
    
    def _update_pagination_ui(self):
        """Update pagination controls."""
        total_pages = (self.total_records - 1) // self.page_size + 1 if self.total_records > 0 else 1
        current_page_display = self.current_page + 1
        
        # Update labels
        start_record = self.current_page * self.page_size + 1
        end_record = min((self.current_page + 1) * self.page_size, self.total_records)
        
        self.status_label.setText(
            f"Εμφάνιση {start_record}-{end_record} από {self.total_records} εγγραφές"
        )
        
        self.page_label.setText(f"Σελίδα {current_page_display} από {total_pages}")
        
        # Update button states
        self.first_page_btn.setEnabled(self.current_page > 0)
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < total_pages - 1)
        self.last_page_btn.setEnabled(self.current_page < total_pages - 1)
    
    def _go_to_first_page(self):
        """Go to first page."""
        self.current_page = 0
        self._load_data()
    
    def _go_to_prev_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._load_data()
    
    def _go_to_next_page(self):
        """Go to next page."""
        total_pages = (self.total_records - 1) // self.page_size + 1
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._load_data()
    
    def _go_to_last_page(self):
        """Go to last page."""
        total_pages = (self.total_records - 1) // self.page_size + 1
        self.current_page = max(0, total_pages - 1)
        self._load_data()
    
    def _on_filter_changed(self):
        """Handle filter change."""
        self.current_page = 0  # Reset to first page
        self._load_data()
    
    def _show_details(self, index: QModelIndex):
        """Show detailed information for selected log entry."""
        if not index.isValid():
            return
        
        record = self.model.get_record(index.row())
        if not record:
            return
        
        # Friendly Greek labels for fields / tables / operations
        FIELD_LABELS = {
            'family_id': 'Πελάτης (κωδ.)', 'client_id': 'Πελάτης (κωδ.)',
            'legacy_code': 'Κωδικός', 'last_name': 'Επώνυμο', 'first_name': 'Όνομα',
            'company_name': 'Επωνυμία', 'afm': 'ΑΦΜ', 'doy': 'ΔΟΥ',
            'national_id': 'ΑΔΤ', 'profession': 'Επάγγελμα',
            'phone': 'Τηλέφωνο', 'mobile': 'Κινητό', 'email': 'Email',
            'address': 'Διεύθυνση', 'city': 'Πόλη', 'postal_code': 'Τ.Κ.',
            'amount': 'Ποσό', 'total_amount': 'Συνολικό ποσό', 'paid_amount': 'Πληρωμένο',
            'remaining_amount': 'Υπόλοιπο', 'status': 'Κατάσταση', 'description': 'Περιγραφή',
            'payment_date': 'Ημ/νία πληρωμής', 'year': 'Έτος',
            'document_type': 'Τύπος παραστατικού', 'receipt_no': 'Αριθμός παραστατικού',
            'vat_rate': 'ΦΠΑ %', 'session_type': 'Τύπος συνεδρίας', 'technician': 'Τεχνικός',
            'duration_minutes': 'Διάρκεια (λεπτά)', 'billed_amount': 'Χρέωση',
            'hourly_rate': 'Χρέωση/ώρα', 'monthly_rate': 'Μηνιαία χρέωση',
            'support_plan': 'Πλάνο', 'is_active': 'Ενεργός',
            'rustdesk_id': 'RustDesk ID', 'notes': 'Σημειώσεις', 'notes_support': 'Σημ. υποστήριξης',
        }
        TABLE_LABELS = {
            'families': 'Πελάτες', 'payments': 'Πληρωμές',
            'support_sessions': 'Συνεδρίες', 'client_package_hours': 'Ώρες Πακέτων',
        }
        OP_LABELS = {'INSERT': 'Προσθήκη', 'UPDATE': 'Τροποποίηση', 'DELETE': 'Διαγραφή'}

        def _fmt_val(key, value):
            if value is None or value == '':
                return '—'
            if key == 'is_active':
                return 'Ναι' if str(value) in ('1', 'True', 'true') else 'Όχι'
            if key == 'document_type':
                return 'Τιμολόγιο' if str(value) == 'invoice' else 'Απόδειξη'
            if key == 'session_type':
                return {'remote': 'RustDesk', 'phone': 'Τηλεφωνική',
                        'onsite': 'Επιτόπου'}.get(str(value), str(value))
            if key == 'support_plan':
                return {'hourly': 'Ωριαία', 'monthly': 'Μηνιαία',
                        'yearly': 'Ετήσια', 'custom': 'Προσαρμοσμένο'}.get(str(value), str(value))
            return value

        def _rows(data):
            html = "<ul>"
            for key, value in data.items():
                lbl = FIELD_LABELS.get(key, key)
                html += f"<li><b>{lbl}:</b> {_fmt_val(key, value)}</li>"
            return html + "</ul>"

        # Format details
        details = f"<h3>Λεπτομέρειες Καταγραφής</h3>"
        details += f"<p><b>Πίνακας:</b> {TABLE_LABELS.get(record['table_name'], record['table_name'])}</p>"
        details += f"<p><b>Εγγραφή #:</b> {record['record_id']}</p>"
        details += f"<p><b>Ενέργεια:</b> {OP_LABELS.get(record['operation'], record['operation'])}</p>"
        details += f"<p><b>Χρήστης:</b> {record['changed_by']}</p>"
        details += f"<p><b>Ημερομηνία:</b> {record['changed_at'].strftime('%d/%m/%Y %H:%M:%S')}</p>"

        # Show old values
        if record.get('old_values'):
            try:
                details += "<p><b>Παλιές Τιμές:</b></p>" + _rows(json.loads(record['old_values']))
            except Exception:
                details += f"<p><b>Παλιές Τιμές:</b> {record['old_values']}</p>"

        # Show new values
        if record.get('new_values'):
            try:
                details += "<p><b>Νέες Τιμές:</b></p>" + _rows(json.loads(record['new_values']))
            except Exception:
                details += f"<p><b>Νέες Τιμές:</b> {record['new_values']}</p>"
        
        # Show dialog
        msg = QMessageBox(self)
        msg.setWindowTitle("Λεπτομέρειες Audit Log")
        msg.setTextFormat(Qt.RichText)
        msg.setText(details)
        msg.exec()
    
    def refresh(self):
        """Refresh the view."""
        # Enforce record limit on refresh
        self._enforce_record_limit()
        self._load_data()

    
    def _export_to_excel(self):
        """Export audit log to Excel file."""
        try:
            from PySide6.QtWidgets import QFileDialog
            from services.export_service import ExportService
            
            # Get current data
            if not self.model._data:
                QMessageBox.information(
                    self,
                    "Πληροφορία",
                    "Δεν υπάρχουν δεδομένα για εξαγωγή."
                )
                return
            
            # Ask for file location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Εξαγωγή Ιστορικού Κινήσεων",
                f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # Prepare data for export
            export_data = []
            for record in self.model._data:
                # Translate operation
                operation_translations = {
                    'INSERT': 'Προσθήκη',
                    'UPDATE': 'Τροποποίηση',
                    'DELETE': 'Διαγραφή'
                }
                operation = operation_translations.get(record.get('operation'), record.get('operation'))
                
                # Translate table name
                table_translations = {
                    'families': 'Πελάτες',
                    'payments': 'Πληρωμές',
                    'subscriptions': 'Συνδρομές',
                    'members': 'Μέλη'
                }
                table_name = table_translations.get(record.get('table_name'), record.get('table_name'))
                
                # Format datetime
                changed_at = record.get('changed_at')
                if isinstance(changed_at, datetime):
                    changed_at = changed_at.strftime('%d/%m/%Y %H:%M:%S')
                
                export_data.append({
                    'ID': record.get('id'),
                    'Πίνακας': table_name,
                    'Record ID': record.get('record_id'),
                    'Ενέργεια': operation,
                    'Χρήστης': record.get('changed_by'),
                    'Ημερομηνία': changed_at,
                    'Παλιές Τιμές': record.get('old_values', ''),
                    'Νέες Τιμές': record.get('new_values', '')
                })
            
            # Export to Excel
            export_service = ExportService()
            success = export_service.export_to_excel(
                data=export_data,
                file_path=file_path,
                sheet_name='Ιστορικό Κινήσεων'
            )
            
            if success:
                QMessageBox.information(
                    self,
                    "Επιτυχία",
                    f"Το ιστορικό κινήσεων εξήχθη επιτυχώς!\n\nΑρχείο: {file_path}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    "Η εξαγωγή απέτυχε. Ελέγξτε το log για λεπτομέρειες."
                )
        
        except Exception as e:
            logger.error(f"Error exporting audit log to Excel: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά την εξαγωγή:\n\n{str(e)}"
            )
    
    def _clear_audit_log(self):
        """Clear all audit log entries from database."""
        try:
            # Confirmation dialog
            reply = gr_question(
                self,
                "Επιβεβαίωση Καθαρισμού",
                "Είστε σίγουροι ότι θέλετε να διαγράψετε ΟΛΟ το ιστορικό κινήσεων;\n\n"
                "Αυτή η ενέργεια ΔΕΝ μπορεί να αναιρεθεί!",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Second confirmation for safety
            reply2 = gr_question(
                self,
                "Τελική Επιβεβαίωση",
                "ΠΡΟΣΟΧΗ: Θα διαγραφούν ΟΛΕΣ οι καταγραφές!\n\n"
                "Συνεχίζετε;",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply2 != QMessageBox.Yes:
                return
            
            # Clear audit log
            count = self.audit_log_repo.clear_all()
            
            # Refresh view
            self.refresh()
            
            QMessageBox.information(
                self,
                "Επιτυχία",
                f"Διαγράφηκαν {count} καταγραφές από το ιστορικό κινήσεων."
            )
            
            logger.info(f"Audit log cleared: {count} records deleted")
        
        except Exception as e:
            logger.error(f"Error clearing audit log: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά τον καθαρισμό:\n\n{str(e)}"
            )
