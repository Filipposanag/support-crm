# -*- coding: utf-8 -*-
"""
Session Form Dialog - Φόρμα Συνεδρίας
Dialog for starting new support sessions.
Διάλογος για έναρξη νέων συνεδριών υποστήριξης.
"""

import logging
from typing import Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QPushButton,
    QLabel, QMessageBox, QDialogButtonBox, QListView, QCompleter
)
from PySide6.QtCore import Qt, Signal, QSize

from db.repositories.clients_repo import ClientsRepository
from db.repositories.sessions_repo import SessionsRepository
from services.session_service import SessionService
from ui.i18n import TranslationManager


def _fmt_remaining(hours) -> str:
    """Decimal hours -> Greek 'X ώρες Y λεπτά' (λεπτά όταν < 1 ώρα). Ίδιο με την ετικέτα πακέτου."""
    tm = int(round(float(hours or 0) * 60))
    hh, mm = divmod(tm, 60)
    wh = "ώρα" if hh == 1 else "ώρες"
    if hh and mm:
        return f"{hh} {wh} {mm} λεπτά"
    if hh:
        return f"{hh} {wh}"
    return f"{mm} λεπτά"

logger = logging.getLogger(__name__)


class SessionForm(QDialog):
    """
    Dialog for starting a new support session.
    Διάλογος για έναρξη νέας συνεδρίας υποστήριξης.
    """
    
    # Signal emitted when session is started
    session_started = Signal(int)  # Emits session_id
    
    def __init__(
        self,
        clients_repo: ClientsRepository,
        sessions_repo: SessionsRepository,
        session_service: SessionService,
        tr_manager: TranslationManager,
        client_id: Optional[int] = None,
        parent=None
    ):
        """
        Initialize SessionForm.
        
        Args:
            clients_repo: ClientsRepository instance
            sessions_repo: SessionsRepository instance
            session_service: SessionService instance
            tr_manager: TranslationManager instance
            client_id: Optional pre-selected client ID
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.clients_repo = clients_repo
        self.sessions_repo = sessions_repo
        self.session_service = session_service
        self.tr_manager = tr_manager
        self.preselected_client_id = client_id
        
        self._init_ui()
        self._connect_signals()
        self._load_clients()
        
        # Pre-select client if provided
        if self.preselected_client_id:
            self._select_client(self.preselected_client_id)
        
        self._on_client_changed()
        logger.debug(f"SessionForm initialized (client_id={client_id})")
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Set dialog properties
        self.setWindowTitle(self.tr_manager.get('start_session'))
        self.setMinimumWidth(500)
        self.setMinimumHeight(450)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel(self.tr_manager.get('new_session'))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Info label
        info_label = QLabel("Συμπληρώστε τα στοιχεία για να ξεκινήσετε νέα συνεδρία υποστήριξης.")
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Form
        form = QFormLayout()
        form.setContentsMargins(0, 10, 0, 10)
        form.setHorizontalSpacing(15)
        form.setVerticalSpacing(12)
        
        # Client selection
        self.client_combo = QComboBox()
        self.client_combo.setMinimumWidth(300)
        self.client_combo.setEditable(True)
        self.client_combo.setInsertPolicy(QComboBox.NoInsert)
        self.client_combo.setMaxVisibleItems(12)
        self.client_combo.lineEdit().setPlaceholderText("Πληκτρολογήστε για αναζήτηση πελάτη...")
        _ccomp = self.client_combo.completer()
        if _ccomp is not None:
            _ccomp.setCompletionMode(QCompleter.PopupCompletion)
            _ccomp.setFilterMode(Qt.MatchContains)
            _ccomp.setCaseSensitivity(Qt.CaseInsensitive)
        form.addRow(self.tr_manager.get('client') + " *:", self.client_combo)

        # Live package / remaining-hours info for the selected client
        self.pkg_info_lbl = QLabel("")
        self.pkg_info_lbl.setWordWrap(True)
        self.pkg_info_lbl.setStyleSheet("color:#78909C;")
        form.addRow("Πακέτο:", self.pkg_info_lbl)

        # Session type — only two options: RustDesk (remote) or phone
        self.session_type_combo = QComboBox()
        self.session_type_combo.addItem("RustDesk", 'remote')
        self.session_type_combo.addItem("Τηλεφωνική", 'phone')
        self.session_type_combo.setMinimumWidth(300)
        self.session_type_combo.setMinimumHeight(34)
        self.session_type_combo.setMaxVisibleItems(10)
        for _i in range(self.session_type_combo.count()):
            self.session_type_combo.setItemData(_i, QSize(0, 36), Qt.SizeHintRole)
        self.session_type_combo.setStyleSheet(
            "QComboBox{combobox-popup:0;}"
            "QComboBox QAbstractItemView::item{min-height:34px;padding:6px 10px;}"
        )
        form.addRow(self.tr_manager.get('session_type') + " *:", self.session_type_combo)
        
        # Technician name
        self.technician_input = QLineEdit()
        self.technician_input.setPlaceholderText("π.χ. Γιάννης Παπαδόπουλος")
        form.addRow(self.tr_manager.get('technician') + ":", self.technician_input)
        # Auto-fill technician with the logged-in user
        try:
            from ui.utils import get_auth_service
            _auth = get_auth_service()
            _cu = _auth.current_user if _auth else None
            if _cu:
                self.technician_input.setText(_cu.get_display_name())
        except Exception:
            pass
        
        layout.addLayout(form)
        
        # Description
        desc_label = QLabel(self.tr_manager.get('session_description') + ":")
        desc_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout.addWidget(desc_label)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        self.description_input.setPlaceholderText(
            "Περιγράψτε το πρόβλημα ή τον λόγο της συνεδρίας..."
        )
        layout.addWidget(self.description_input)
        
        # RustDesk Session ID (optional, for remote sessions)
        self.rustdesk_id_input = QLineEdit()
        self.rustdesk_id_input.setPlaceholderText("Προαιρετικό - Αυτόματο για απομακρυσμένες συνεδρίες")
        
        # RustDesk connect button
        rustdesk_layout = QHBoxLayout()
        rustdesk_label = QLabel("RustDesk Session ID:")
        rustdesk_label.setMinimumWidth(150)
        rustdesk_layout.addWidget(rustdesk_label)
        rustdesk_layout.addWidget(self.rustdesk_id_input, stretch=1)
        
        self.rustdesk_connect_btn = QPushButton("Σύνδεση RustDesk")
        self.rustdesk_connect_btn.setStyleSheet("QPushButton{background-color:#1976D2;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#1565C0;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        self.rustdesk_connect_btn.clicked.connect(self._on_rustdesk_connect)
        rustdesk_layout.addWidget(self.rustdesk_connect_btn)
        
        layout.addLayout(rustdesk_layout)
        
        layout.addStretch()
        
        # Info about timer
        timer_info = QLabel(
            "⏱️ Το χρονόμετρο θα ξεκινήσει αυτόματα μετά την αποθήκευση."
        )
        timer_info.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                color: #1976D2;
                padding: 10px;
                border-radius: 5px;
                border-left: 4px solid #2196F3;
            }
        """)
        timer_info.setWordWrap(True)
        layout.addWidget(timer_info)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.button(QDialogButtonBox.Save).setText(
            self.tr_manager.get('btn_start')
        )
        button_box.button(QDialogButtonBox.Cancel).setText(
            self.tr_manager.get('btn_cancel')
        )
        
        # Style the start button
        start_btn = button_box.button(QDialogButtonBox.Save)
        start_btn.setStyleSheet("QPushButton{background-color:#4CAF50;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#45a049;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        
        layout.addWidget(button_box)
        
        self.button_box = button_box
    
    def _connect_signals(self):
        """Connect signals to slots."""
        self.button_box.accepted.connect(self._on_start_session)
        self.button_box.rejected.connect(self.reject)
        
        # Update RustDesk ID visibility based on session type
        self.session_type_combo.currentIndexChanged.connect(self._on_session_type_changed)

        # Show the selected client's package / remaining hours
        self.client_combo.currentIndexChanged.connect(self._on_client_changed)
    
    def _on_client_changed(self):
        """Show the selected client's active package(s) and remaining hours."""
        if not hasattr(self, "pkg_info_lbl"):
            return
        client_id = self.client_combo.currentData()
        if not client_id:
            self.pkg_info_lbl.setText("")
            return
        db = getattr(self.clients_repo, "db", None)
        if not db:
            self.pkg_info_lbl.setText("")
            return
        try:
            rows = db.execute_query(
                "SELECT sp.name nm, cph.remaining_hours rh "
                "FROM client_package_hours cph "
                "JOIN support_packages sp ON sp.id = cph.package_id "
                "WHERE cph.client_id=%s AND cph.is_active=1 "
                "AND (cph.expiry_date IS NULL OR cph.expiry_date >= CURDATE()) "
                "AND cph.remaining_hours > 0 "
                "ORDER BY cph.expiry_date ASC", (client_id,))
        except Exception as e:
            logger.error(f"package info query failed: {e}")
            rows = []
        if rows:
            total = sum(float(r.get("rh") or 0) for r in rows)
            names = []
            for r in rows:
                n = r.get("nm")
                if n and n not in names:
                    names.append(n)
            label_pkg = ", ".join(names[:2]) + ("…" if len(names) > 2 else "")
            htxt = _fmt_remaining(total)
            color = "#2E7D32" if total >= 2 else "#EF6C00"
            self.pkg_info_lbl.setText(f"📦 {label_pkg}  ·  Υπόλοιπο: {htxt}")
            self.pkg_info_lbl.setStyleSheet(f"color:{color};font-weight:bold;")
        else:
            self.pkg_info_lbl.setText("📦 Χωρίς ενεργό πακέτο — ωριαία χρέωση")
            self.pkg_info_lbl.setStyleSheet("color:#78909C;")

        # Auto-fill the client's stored RustDesk ID into the optional field.
        try:
            if hasattr(self, "rustdesk_id_input"):
                client = self.clients_repo.get_client_by_id(client_id)
                rd = (client.get("rustdesk_id", "") or "").strip() if client else ""
                self.rustdesk_id_input.setText(rd)
        except Exception as e:
            logger.error(f"rustdesk autofill failed: {e}")

    def _on_session_type_changed(self):
        """Handle session type change."""
        session_type = self.session_type_combo.currentData()
        
        # Show RustDesk ID field only for remote sessions
        is_remote = session_type == 'remote'
        self.rustdesk_id_input.setVisible(is_remote)
        self.rustdesk_connect_btn.setVisible(is_remote)
    
    def _on_rustdesk_connect(self):
        """Handle RustDesk connect button click."""
        try:
            # Get selected client
            client_id = self.client_combo.currentData()
            if not client_id:
                QMessageBox.warning(
                    self,
                    self.tr_manager.get('warning'),
                    "Παρακαλώ επιλέξτε πρώτα έναν πελάτη."
                )
                return
            
            # Get client details
            client = self.clients_repo.get_client_by_id(client_id)
            if not client:
                QMessageBox.warning(
                    self,
                    self.tr_manager.get('warning'),
                    "Δεν βρέθηκε ο πελάτης."
                )
                return
            
            # Check if client has RustDesk ID
            rustdesk_id = client.get('rustdesk_id', '').strip()
            if not rustdesk_id:
                QMessageBox.warning(
                    self,
                    "RustDesk ID Απαιτείται",
                    f"Ο πελάτης δεν έχει RustDesk ID.\n\n"
                    f"Παρακαλώ προσθέστε το RustDesk ID στα στοιχεία του πελάτη."
                )
                return
            
            # Get RustDesk password (if available)
            rustdesk_password = client.get('rustdesk_password', '').strip()
            
            # Initialize RustDesk service
            from services.rustdesk_service import RustDeskService
            from services.settings_service import SettingsService
            from db.connection import DatabaseConnection
            
            # Get RustDesk settings
            from config import DATABASE_CONFIG
            db_connection = DatabaseConnection(DATABASE_CONFIG)
            settings_service = SettingsService(db_connection)
            settings = settings_service.load_settings()
            
            rustdesk_service = RustDeskService()
            
            # Configure custom server if specified
            if settings and settings.rustdesk_server_host:
                rustdesk_service.configure_server(
                    host=settings.rustdesk_server_host,
                    port=settings.rustdesk_server_port,
                    api_key=settings.rustdesk_api_key
                )
            
            # Check if RustDesk is available
            if not rustdesk_service.is_available():
                QMessageBox.warning(
                    self,
                    "RustDesk Μη Διαθέσιμο",
                    "Το RustDesk δεν βρέθηκε στο σύστημα.\n\n"
                    "Παρακαλώ εγκαταστήστε το RustDesk από:\n"
                    "https://rustdesk.com/"
                )
                return
            
            # Connect to client
            success = rustdesk_service.connect_to_client(
                rustdesk_id=rustdesk_id,
                password=rustdesk_password if rustdesk_password else None
            )
            
            if success:
                # Update RustDesk session ID field
                self.rustdesk_id_input.setText(rustdesk_id)
                
                QMessageBox.information(
                    self,
                    "Σύνδεση Ξεκίνησε",
                    f"Η σύνδεση RustDesk ξεκίνησε!\n\n"
                    f"RustDesk ID: {rustdesk_id}\n\n"
                    f"Το RustDesk θα ανοίξει σε λίγο."
                )
                logger.info(f"RustDesk connection initiated to client {client_id}")
            else:
                QMessageBox.critical(
                    self,
                    self.tr_manager.get('error'),
                    "Αποτυχία εκκίνησης σύνδεσης RustDesk.\n\n"
                    "Ελέγξτε τα logs για περισσότερες πληροφορίες."
                )
                
        except Exception as e:
            logger.error(f"Error connecting via RustDesk: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                self.tr_manager.get('error'),
                f"Σφάλμα σύνδεσης RustDesk:\n{str(e)}"
            )
    
    def _load_clients(self):
        """Load active clients into combo box."""
        try:
            # Get active clients
            clients = self.clients_repo.list_clients(only_active=True, limit=1000)
            
            # Clear combo
            self.client_combo.clear()
            
            # Add clients
            for client in clients:
                # Format display name
                if client.get('company_name'):
                    display_name = client['company_name']
                else:
                    display_name = f"{client.get('last_name', '')} {client.get('first_name', '')}".strip()
                
                # Add code if available
                if client.get('legacy_code'):
                    display_name = f"[{client['legacy_code']}] {display_name}"
                
                self.client_combo.addItem(display_name, client['id'])
                self.client_combo.setItemData(self.client_combo.count() - 1, QSize(0, 32), Qt.SizeHintRole)
            
            logger.debug(f"Loaded {len(clients)} clients into combo box")
            
        except Exception as e:
            logger.error(f"Error loading clients: {e}")
            QMessageBox.critical(
                self,
                self.tr_manager.get('error'),
                f"Σφάλμα φόρτωσης πελατών: {str(e)}"
            )
    
    def _select_client(self, client_id: int):
        """Select a specific client in the combo box."""
        for i in range(self.client_combo.count()):
            if self.client_combo.itemData(i) == client_id:
                self.client_combo.setCurrentIndex(i)
                break
    
    def _validate_form(self) -> bool:
        """Validate form data."""
        # Check client selection
        if self.client_combo.currentIndex() < 0:
            QMessageBox.warning(
                self,
                self.tr_manager.get('warning'),
                self.tr_manager.get('msg_client_required')
            )
            self.client_combo.setFocus()
            return False
        
        return True
    
    def _on_start_session(self):
        """Handle start session button click."""
        if not self._validate_form():
            return
        
        try:
            # Get form data
            client_id = self.client_combo.currentData()
            session_type = self.session_type_combo.currentData()
            technician = self.technician_input.text().strip()
            description = self.description_input.toPlainText().strip()
            rustdesk_session_id = self.rustdesk_id_input.text().strip()
            
            # Check prepaid hours balance (warning only, doesn't block)
            self._check_prepaid_hours_balance(client_id)
            
            # Start session
            session_id = self.session_service.start_session(
                client_id=client_id,
                session_type=session_type,
                technician=technician,
                description=description,
                rustdesk_session_id=rustdesk_session_id
            )
            
            if session_id:
                QMessageBox.information(
                    self,
                    self.tr_manager.get('success'),
                    self.tr_manager.get('msg_session_started')
                )
                self.session_started.emit(session_id)
                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    self.tr_manager.get('warning'),
                    "Αποτυχία έναρξης συνεδρίας"
                )
                
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            QMessageBox.critical(
                self,
                self.tr_manager.get('error'),
                f"Σφάλμα έναρξης συνεδρίας: {str(e)}"
            )

    def _check_prepaid_hours_balance(self, client_id: int):
        """
        Check client's prepaid hours balance and show warning if low.
        
        Args:
            client_id: Client ID to check
        """
        try:
            # Get database connection from clients_repo
            db_connection = self.clients_repo.db if hasattr(self.clients_repo, 'db') else None
            if not db_connection:
                return
            
            # Query remaining hours
            query = """
                SELECT SUM(remaining_hours) as total_hours
                FROM client_package_hours
                WHERE client_id = %s
                AND is_active = 1
                AND (expiry_date IS NULL OR expiry_date >= CURDATE())
            """
            
            results = db_connection.execute_query(query, (client_id,))
            
            if results and len(results) > 0:
                total_hours = results[0].get('total_hours')
                
                if total_hours is not None:
                    total_hours = float(total_hours)
                    
                    # Show warning if hours are low
                    if total_hours <= 0:
                        QMessageBox.warning(
                            self,
                            "⚠️ Ανεπαρκές Υπόλοιπο Ωρών",
                            f"Ο πελάτης δεν έχει διαθέσιμες προπληρωμένες ώρες.\n\n"
                            f"Υπόλοιπο: {_fmt_remaining(total_hours)}\n\n"
                            f"Η συνεδρία θα ξεκινήσει κανονικά, αλλά ο πελάτης θα χρεωθεί "
                            f"με βάση το ωριαίο τιμολόγιο."
                        )
                    elif total_hours < 2:
                        box = QMessageBox(self)
                        box.setIcon(QMessageBox.Warning)
                        box.setWindowTitle("⚠️ Χαμηλό Υπόλοιπο Ωρών")
                        box.setText(
                            f"Ο πελάτης έχει χαμηλό υπόλοιπο προπληρωμένων ωρών.\n\n"
                            f"Υπόλοιπο: {_fmt_remaining(total_hours)}\n\n"
                            f"Θέλετε να συνεχίσετε;"
                        )
                        _yes = box.addButton("Ναι", QMessageBox.YesRole)
                        _no = box.addButton("Όχι", QMessageBox.NoRole)
                        box.setDefaultButton(_yes)
                        box.exec()
                        
                        if box.clickedButton() is _no:
                            # User chose not to continue
                            raise ValueError("Ο χρήστης ακύρωσε τη συνεδρία λόγω χαμηλού υπολοίπου")
                    elif total_hours < 5:
                        # Just inform, don't block
                        QMessageBox.information(
                            self,
                            "ℹ️ Υπόλοιπο Ωρών",
                            f"Ο πελάτης έχει {_fmt_remaining(total_hours)} διαθέσιμες.\n\n"
                            f"Η συνεδρία θα ξεκινήσει κανονικά."
                        )
                        
        except ValueError:
            # Re-raise ValueError to stop session creation
            raise
        except Exception as e:
            logger.error(f"Error checking prepaid hours balance: {e}")
            # Don't block session creation on error
