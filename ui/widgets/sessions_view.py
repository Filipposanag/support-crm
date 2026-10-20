# -*- coding: utf-8 -*-
"""
Sessions View - Προβολή Συνεδριών
Main view for displaying and managing support sessions.
Κύρια προβολή για εμφάνιση και διαχείριση συνεδριών υποστήριξης.
"""

import logging
from typing import Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QPushButton, QTableView, QLabel, QMessageBox, QHeaderView, QDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem

from db.repositories.sessions_repo import SessionsRepository
from db.repositories.clients_repo import ClientsRepository
from services.session_service import SessionService
from ui.i18n import TranslationManager
from resources.icons import get_icon
from ui.utils.permission_helper import has_permission

logger = logging.getLogger(__name__)


class SessionsView(QWidget):
    """
    Main view for sessions management.
    Κύρια προβολή για διαχείριση συνεδριών.
    
    Features / Χαρακτηριστικά:
    - Active sessions display / Εμφάνιση ενεργών συνεδριών
    - Session history / Ιστορικό συνεδριών
    - Start/Stop session / Έναρξη/Λήξη συνεδρίας
    - Session timer / Χρονόμετρο συνεδρίας
    - Auto-billing / Αυτόματη χρέωση
    """
    
    def __init__(
        self,
        sessions_repo: SessionsRepository,
        clients_repo: ClientsRepository,
        session_service: SessionService,
        tr_manager: TranslationManager,
        rustdesk_service=None,
        parent=None
    ):
        """
        Initialize SessionsView.
        
        Args:
            sessions_repo: SessionsRepository instance
            clients_repo: ClientsRepository instance
            session_service: SessionService instance
            tr_manager: TranslationManager instance
            rustdesk_service: RustDeskService instance (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.sessions_repo = sessions_repo
        self.clients_repo = clients_repo
        self.session_service = session_service
        self.tr_manager = tr_manager
        self.rustdesk_service = rustdesk_service
        
        # Filter state
        self.search_text = ""
        self.status_filter = "all"  # all, active, completed, cancelled
        
        # Active session tracking
        self.active_session_id = None
        self.session_start_time = None

        # Cache of loaded sessions by id (for the details dialog)
        self._sessions_by_id = {}

        # Timer for updating elapsed time
        self.timer = QTimer()
        self.timer.setInterval(1000)  # Update every second
        self.timer.timeout.connect(self._update_timer_display)
        
        self._init_ui()
        self._connect_signals()
        
        # Initial load
        self.refresh()
        
        logger.debug("SessionsView initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel(self.tr_manager.get('sessions'))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Active session panel
        active_session_layout = self._create_active_session_panel()
        layout.addLayout(active_session_layout)
        
        # Filter bar
        filter_layout = self._create_filter_bar()
        layout.addLayout(filter_layout)
        
        # Table view
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.setEditTriggers(QTableView.NoEditTriggers)  # Disable editing
        
        # Create model
        self.table_model = QStandardItemModel()
        self.table_view.setModel(self.table_model)
        
        # Set column headers
        self._setup_table_columns()
        
        layout.addWidget(self.table_view, stretch=1)
        
        # Action buttons
        button_layout = self._create_action_buttons()
        layout.addLayout(button_layout)
    
    def _create_active_session_panel(self) -> QHBoxLayout:
        """Create active session panel with timer."""
        panel_layout = QHBoxLayout()
        panel_layout.setSpacing(10)
        
        # Active session indicator
        self.active_session_label = QLabel("Δεν υπάρχει ενεργή συνεδρία")
        self.active_session_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        panel_layout.addWidget(self.active_session_label, stretch=1)
        
        # Timer display
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setStyleSheet("""
            QLabel {
                background-color: #2196F3;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 18px;
                font-weight: bold;
                font-family: monospace;
            }
        """)
        self.timer_label.setVisible(False)
        panel_layout.addWidget(self.timer_label)
        
        # Stop session button
        self.stop_session_btn = QPushButton(
            get_icon('delete'),
            self.tr_manager.get('end_session')
        )
        self.stop_session_btn.setStyleSheet("QPushButton{background-color:#E53935;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#C62828;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        self.stop_session_btn.setVisible(False)
        panel_layout.addWidget(self.stop_session_btn)
        
        return panel_layout
    
    def _create_filter_bar(self) -> QHBoxLayout:
        """Create the filter bar."""
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Αναζήτηση πελάτη ή τεχνικού...")
        self.search_input.setMinimumWidth(300)
        filter_layout.addWidget(self.search_input)
        
        # Status filter
        status_label = QLabel("Κατάσταση:")
        filter_layout.addWidget(status_label)
        
        self.status_combo = QComboBox()
        self.status_combo.addItem("Όλες", "all")
        self.status_combo.addItem("Ενεργές", "active")
        self.status_combo.addItem("Ολοκληρωμένες", "completed")
        self.status_combo.addItem("Ακυρωμένες", "cancelled")
        filter_layout.addWidget(self.status_combo)
        
        # Refresh button
        self.refresh_btn = QPushButton(
            get_icon('refresh'),
            self.tr_manager.get('btn_refresh')
        )
        filter_layout.addWidget(self.refresh_btn)
        
        filter_layout.addStretch()
        
        return filter_layout
    
    def _create_action_buttons(self) -> QHBoxLayout:
        """Create action buttons."""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Start new session button
        self.new_session_btn = QPushButton(
            get_icon('add'),
            self.tr_manager.get('start_session')
        )
        self.new_session_btn.setStyleSheet("QPushButton{background-color:#4CAF50;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#45a049;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        button_layout.addWidget(self.new_session_btn)
        
        # View details button
        self.view_btn = QPushButton(
            get_icon('search'),
            "Προβολή Λεπτομερειών"
        )
        self.view_btn.setEnabled(False)
        button_layout.addWidget(self.view_btn)
        
        button_layout.addStretch()
        
        # Records count label
        self.records_label = QLabel()
        button_layout.addWidget(self.records_label)
        
        return button_layout
    
    def _setup_table_columns(self):
        """Setup table columns."""
        headers = [
            "ID",
            self.tr_manager.get('client_name').replace('_', ' '),
            self.tr_manager.get('session_type').replace('_', ' '),
            self.tr_manager.get('start_time').replace('_', ' '),
            self.tr_manager.get('end_time').replace('_', ' '),
            self.tr_manager.get('duration_minutes').replace('_', ' '),
            self.tr_manager.get('technician').replace('_', ' '),
            self.tr_manager.get('billed_amount').replace('_', ' '),
            self.tr_manager.get('status').replace('_', ' '),
        ]
        self.table_model.setHorizontalHeaderLabels(headers)
        
        # Set column widths - Make all columns interactive (resizable)
        header = self.table_view.horizontalHeader()
        header.setStretchLastSection(False)
        # Allow user to resize all columns
        header.setSectionResizeMode(QHeaderView.Interactive)
        
        # Load saved column widths or use defaults
        self._load_column_widths()
        
        # Connect signal to save column widths when changed
        header.sectionResized.connect(self._on_column_resized)
    
    def _load_column_widths(self):
        """Load saved column widths from settings."""
        from PySide6.QtCore import QSettings
        settings = QSettings('SupportCRM', 'ColumnWidths')
        
        # Default widths
        default_widths = [50, 150, 120, 140, 140, 100, 120, 100, 100]
        
        header = self.table_view.horizontalHeader()
        for i, default_width in enumerate(default_widths):
            # Load saved width or use default
            width = settings.value(f'sessions_view/column_{i}', default_width, type=int)
            header.resizeSection(i, width)
    
    def _on_column_resized(self, index, old_size, new_size):
        """Save column width when resized."""
        from PySide6.QtCore import QSettings
        settings = QSettings('SupportCRM', 'ColumnWidths')
        settings.setValue(f'sessions_view/column_{index}', new_size)
    
    def _connect_signals(self):
        """Connect signals to slots."""
        # Search input
        self.search_input.textChanged.connect(self._on_search_changed)
        
        # Status filter
        self.status_combo.currentIndexChanged.connect(self._apply_filters)
        
        # Refresh button
        self.refresh_btn.clicked.connect(self.refresh)
        
        # Action buttons
        self.new_session_btn.clicked.connect(self._on_start_session)
        self.stop_session_btn.clicked.connect(self._on_stop_session)
        self.view_btn.clicked.connect(self._on_view_details)
        
        # Table selection
        self.table_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

        # Double-click a row to open its details
        self.table_view.doubleClicked.connect(self._on_view_details)
    
    def _on_search_changed(self, text: str):
        """Handle search text change."""
        self.search_text = text
        self.refresh()
    
    def _apply_filters(self):
        """Apply current filters and refresh data."""
        self.refresh()
    
    def refresh(self):
        """Refresh the table data."""
        try:
            # Get filter values
            search = self.search_text.strip()
            status = self.status_combo.currentData()
            
            # Fetch data
            sessions = self.sessions_repo.list_sessions(
                search=search if search else None,
                status=status if status != "all" else None,
                limit=100,
                offset=0
            )
            
            # Update table
            self._populate_table(sessions)
            
            # Update records label
            self.records_label.setText(f"Σύνολο: {len(sessions)}")
            
            # Check for active sessions
            self._check_active_sessions()
            
            logger.debug(f"Refreshed sessions view: {len(sessions)} records")
            
        except Exception as e:
            logger.error(f"Error refreshing sessions view: {e}")
            QMessageBox.critical(
                self,
                self.tr_manager.get('error'),
                f"Σφάλμα φόρτωσης δεδομένων: {str(e)}"
            )
    
    def _populate_table(self, sessions: list):
        """Populate table with session data."""
        self.table_model.removeRows(0, self.table_model.rowCount())

        # Keep the full records so the details dialog can show every field
        self._sessions_by_id = {s.get('id'): s for s in sessions}

        for session in sessions:
            row = []
            
            # ID
            row.append(QStandardItem(str(session.get('id', ''))))
            
            # Client name
            last_name = session.get('last_name', '') or ''
            first_name = session.get('first_name', '') or ''
            client_name = f"{last_name} {first_name}".strip()
            if not client_name:
                client_name = "Άγνωστος"
            row.append(QStandardItem(client_name))
            
            # Session type
            session_type = session.get('session_type', 'remote')
            type_display = {
                'remote': 'Απομακρυσμένη',
                'onsite': 'Επιτόπου',
                'phone': 'Τηλεφωνική',
                'email': 'Email/Chat'
            }.get(session_type, session_type)
            row.append(QStandardItem(type_display))
            
            # Start time
            start_time = session.get('start_time')
            if start_time:
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time)
                row.append(QStandardItem(start_time.strftime('%d/%m/%Y %H:%M')))
            else:
                row.append(QStandardItem('-'))
            
            # End time
            end_time = session.get('end_time')
            if end_time:
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time)
                row.append(QStandardItem(end_time.strftime('%d/%m/%Y %H:%M')))
            else:
                row.append(QStandardItem('-'))
            
            # Duration
            duration_seconds = session.get('duration_seconds', 0)
            duration_minutes = session.get('duration_minutes', 0)
            
            if duration_seconds > 0:
                # Show minutes and seconds
                minutes = duration_seconds // 60
                seconds = duration_seconds % 60
                duration_text = f"{minutes}λ {seconds}δ"
            elif duration_minutes > 0:
                # Fallback to minutes only (old data)
                duration_text = f"{duration_minutes} λεπτά"
            else:
                duration_text = "0λ 0δ"
            
            row.append(QStandardItem(duration_text))
            
            # Technician
            row.append(QStandardItem(session.get('technician', '-')))
            
            # Billed amount
            amount = session.get('billed_amount', 0)
            row.append(QStandardItem(f"{amount:.2f} €"))
            
            # Status
            status = str(session.get('status', 'active')).strip().lower()
            status_display = {
                'active': 'Ενεργή',
                'completed': 'Ολοκληρωμένη',
                'cancelled': 'Ακυρωμένη',
                'canceled': 'Ακυρωμένη'
            }.get(status, 'Άγνωστη')
            row.append(QStandardItem(status_display))
            
            # Store session ID in first column
            row[0].setData(session.get('id'), Qt.UserRole)
            
            self.table_model.appendRow(row)
    
    def _check_active_sessions(self):
        """Check for active sessions and update UI."""
        try:
            active_sessions = self.session_service.get_active_sessions()
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            active_sessions = []
        
        if active_sessions:
            # Show first active session
            session = active_sessions[0]
            self.active_session_id = session.get('id') if isinstance(session, dict) else session.id
            
            # Get start_time - handle both string and datetime
            start_time = session.get('start_time') if isinstance(session, dict) else session.start_time
            
            # Validate start_time type
            from datetime import datetime, timedelta
            
            if isinstance(start_time, timedelta):
                # Invalid data from database - skip this session
                logger.error(f"Invalid start_time type (timedelta) for session {self.active_session_id}")
                self.active_session_id = None
                self.session_start_time = None
            elif isinstance(start_time, str):
                try:
                    self.session_start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                except Exception as e:
                    logger.error(f"Error parsing start_time string: {e}")
                    self.session_start_time = None
            elif isinstance(start_time, datetime):
                # It's already a datetime object
                self.session_start_time = start_time
            else:
                logger.error(f"Unknown start_time type: {type(start_time)}")
                self.session_start_time = None
            
            # Only show active session if we have valid start_time
            if self.session_start_time:
                # Update UI
                client_id = session.get('client_id') if isinstance(session, dict) else session.client_id
                client = self.clients_repo.get_client_by_id(client_id)
                client_name = "Άγνωστος"
                if client:
                    last_name = client.get('last_name', '') or ''
                    first_name = client.get('first_name', '') or ''
                    client_name = f"{last_name} {first_name}".strip()
                    if not client_name:
                        client_name = "Άγνωστος"
                
                self.active_session_label.setText(f"Ενεργή συνεδρία: {client_name}")
                self.active_session_label.setStyleSheet("""
                    QLabel {
                        background-color: #4CAF50;
                        color: white;
                        padding: 10px;
                        border-radius: 5px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
                
                self.timer_label.setVisible(True)
                self.stop_session_btn.setVisible(True)
                self.new_session_btn.setEnabled(False)
                
                # Start timer
                if not self.timer.isActive():
                    self.timer.start()
                return
        
        # No active sessions or invalid session data
        self.active_session_id = None
        self.session_start_time = None
        
        self.active_session_label.setText("Δεν υπάρχει ενεργή συνεδρία")
        self.active_session_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        
        self.timer_label.setVisible(False)
        self.stop_session_btn.setVisible(False)
        self.new_session_btn.setEnabled(True)
        
        # Stop timer
        if self.timer.isActive():
            self.timer.stop()
    
    def _update_timer_display(self):
        """Update the timer display."""
        if not self.session_start_time:
            return
        
        try:
            from datetime import datetime
            
            # Ensure session_start_time is datetime object
            if isinstance(self.session_start_time, str):
                self.session_start_time = datetime.fromisoformat(self.session_start_time.replace('Z', '+00:00'))
            
            # Calculate elapsed time (should be timedelta)
            now = datetime.now()
            
            # Make sure both are datetime objects
            if not isinstance(self.session_start_time, datetime):
                logger.error(f"session_start_time is not datetime: {type(self.session_start_time)}")
                return
            
            elapsed = now - self.session_start_time
            
            # Get total seconds from timedelta
            total_seconds = elapsed.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            
            self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
        except Exception as e:
            logger.error(f"Error updating timer display: {e}", exc_info=True)
            # Stop timer on error
            if self.timer.isActive():
                self.timer.stop()
    
    def _on_selection_changed(self):
        """Handle table selection change."""
        has_selection = self.table_view.selectionModel().hasSelection()
        self.view_btn.setEnabled(has_selection)
    
    def _on_start_session(self):
        """Handle start session button click."""
        if not has_permission('sessions.create'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα δημιουργίας συνεδρίας.")
            return
        from ui.widgets.session_form import SessionForm
        
        dialog = SessionForm(
            clients_repo=self.clients_repo,
            sessions_repo=self.sessions_repo,
            session_service=self.session_service,
            tr_manager=self.tr_manager,
            parent=self
        )
        dialog.session_started.connect(lambda: self.refresh())
        dialog.exec()
    
    def start_session_for_client(self, client_id: int, client_name: str = None) -> bool:
        """
        Start a new session for a specific client (auto-start from RustDesk).
        
        Args:
            client_id: Client ID
            client_name: Client name (optional, for display)
            
        Returns:
            True if session started successfully
        """
        try:
            # Check if there's already an active session
            active_sessions = self.session_service.get_active_sessions()
            if active_sessions:
                # Already have an active session
                logger.warning(f"Cannot start new session - active session exists")
                return False
            
            # Start new session
            session_id = self.session_service.start_session(
                client_id=client_id,
                technician="",  # Will be filled by user later
                issue_description="Απομακρυσμένη υποστήριξη μέσω RustDesk"
            )
            
            if session_id:
                logger.info(f"Auto-started session {session_id} for client {client_id}")
                
                # Refresh to show the new session
                self.refresh()
                
                # Show notification
                if client_name:
                    self.active_session_label.setText(f"Ενεργή συνεδρία: {client_name}")
                
                return True
            else:
                logger.error("Failed to start session")
                return False
                
        except Exception as e:
            logger.error(f"Error auto-starting session: {e}", exc_info=True)
            return False
    
    def _on_stop_session(self):
        if not has_permission('sessions.edit'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα τερματισμού/επεξεργασίας συνεδρίας.")
            return
        """Handle stop session button click."""
        if not self.active_session_id:
            return
        
        _box = QMessageBox(self)
        _box.setIcon(QMessageBox.Question)
        _box.setWindowTitle(self.tr_manager.get('end_session'))
        _box.setText(self.tr_manager.get('msg_confirm_end_session'))
        _box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        _box.button(QMessageBox.Yes).setText(self.tr_manager.get('btn_yes'))
        _box.button(QMessageBox.No).setText(self.tr_manager.get('btn_no'))
        _box.setDefaultButton(QMessageBox.No)
        reply = _box.exec()
        
        if reply == QMessageBox.Yes:
            try:
                # Determine session type for the correct closing message
                _stype = 'remote'
                try:
                    _db0 = getattr(self.clients_repo, 'db', None)
                    if _db0 is not None:
                        _tr = _db0.execute_query(
                            "SELECT session_type FROM support_sessions WHERE id=%s",
                            (self.active_session_id,))
                        if _tr:
                            _stype = _tr[0].get('session_type') or 'remote'
                except Exception:
                    _stype = 'remote'

                # Close RustDesk only for RustDesk (remote) sessions
                if _stype == 'remote' and self.rustdesk_service:
                    try:
                        self.rustdesk_service.disconnect_all()
                        logger.info("RustDesk connection closed")
                    except Exception as e:
                        logger.warning(f"Failed to close RustDesk: {e}")
                
                # End session with auto-billing
                success = self.session_service.end_session(
                    self.active_session_id,
                    issue_summary="",
                    auto_bill=True
                )
                
                if success:
                    if _stype == 'phone':
                        _end_msg = "Η τηλεφωνική συνεδρία ολοκληρώθηκε επιτυχώς."
                    else:
                        _end_msg = "Η συνεδρία ολοκληρώθηκε επιτυχώς.\nΗ σύνδεση RustDesk έκλεισε αυτόματα."
                    QMessageBox.information(
                        self,
                        self.tr_manager.get('success'),
                        _end_msg
                    )
                    # Προσφορά έκδοσης απόδειξης/τιμολογίου για χρεωμένη συνεδρία (χωρίς πακέτο)
                    try:
                        _ended_id = self.active_session_id
                        _db = getattr(self.clients_repo, 'db', None)
                        if _db is not None and _ended_id:
                            _r = _db.execute_query("SELECT payment_id FROM support_sessions WHERE id=%s", (_ended_id,))
                            _pid = _r[0]['payment_id'] if _r else None
                            if _pid:
                                _p = _db.execute_query("SELECT paid_amount, total_amount FROM payments WHERE id=%s", (_pid,))
                                _amt = (float(_p[0].get('paid_amount') or 0) or float(_p[0].get('total_amount') or 0)) if _p else 0.0
                                if _amt > 0:
                                    from ui.widgets.document_type_dialog import issue_document_from_db
                                    issue_document_from_db(self, _pid, _db, clients_repo=self.clients_repo)
                    except Exception as _e:
                        logger.warning(f"Could not offer document issuance: {_e}")
                    self.refresh()
                else:
                    QMessageBox.warning(
                        self,
                        self.tr_manager.get('warning'),
                        "Αποτυχία λήξης συνεδρίας"
                    )
                    
            except Exception as e:
                logger.error(f"Error ending session: {e}")
                QMessageBox.critical(
                    self,
                    self.tr_manager.get('error'),
                    f"Σφάλμα λήξης συνεδρίας: {str(e)}"
                )
    
    def _get_selected_session_id(self):
        """Return the id of the currently selected session, or None."""
        selection = self.table_view.selectionModel()
        if not selection or not selection.hasSelection():
            return None
        row = selection.selectedRows()
        if row:
            index = row[0]
        else:
            index = selection.currentIndex()
        if not index.isValid():
            return None
        # The session id is stored on the first column (Qt.UserRole)
        id_item = self.table_model.item(index.row(), 0)
        if id_item is None:
            return None
        session_id = id_item.data(Qt.UserRole)
        if session_id is None:
            session_id = id_item.text()
        return session_id

    def _on_view_details(self, *args):
        """Open a dialog with the full details of the selected session."""
        session_id = self._get_selected_session_id()
        if session_id is None:
            QMessageBox.information(
                self,
                "Λεπτομέρειες Συνεδρίας",
                "Επιλέξτε πρώτα μια συνεδρία από τη λίστα."
            )
            return

        session = self._sessions_by_id.get(session_id)
        if session is None:
            # Fallback: try to match by string id
            for sid, data in self._sessions_by_id.items():
                if str(sid) == str(session_id):
                    session = data
                    break

        if session is None:
            QMessageBox.warning(
                self,
                self.tr_manager.get('warning'),
                "Δεν βρέθηκαν στοιχεία για τη συνεδρία."
            )
            return

        self._show_session_details_dialog(session)

    def _show_session_details_dialog(self, session: dict):
        """Build and show a read-only details dialog for a session."""
        from PySide6.QtWidgets import (
            QDialog, QFormLayout, QDialogButtonBox, QGroupBox, QTextEdit
        )

        def fmt_datetime(value):
            if not value:
                return '-'
            if isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except Exception:
                    return value
            try:
                return value.strftime('%d/%m/%Y %H:%M')
            except Exception:
                return str(value)

        # Client name
        last_name = session.get('last_name', '') or ''
        first_name = session.get('first_name', '') or ''
        client_name = f"{last_name} {first_name}".strip() or "Άγνωστος"

        # Session type (human readable)
        type_display = {
            'remote': 'Απομακρυσμένη',
            'onsite': 'Επιτόπου',
            'phone': 'Τηλεφωνική',
            'email': 'Email/Chat'
        }.get(session.get('session_type', 'remote'), session.get('session_type', '-'))

        # Status (human readable)
        status_display = {
            'active': 'Ενεργή',
            'completed': 'Ολοκληρωμένη',
            'cancelled': 'Ακυρωμένη'
        }.get(session.get('status', 'active'), session.get('status', '-'))

        # Duration
        duration_seconds = session.get('duration_seconds', 0) or 0
        duration_minutes = session.get('duration_minutes', 0) or 0
        if duration_seconds > 0:
            duration_text = f"{duration_seconds // 60}λ {duration_seconds % 60}δ"
        elif duration_minutes > 0:
            duration_text = f"{duration_minutes} λεπτά"
        else:
            duration_text = "0λ 0δ"

        # Billed amount
        try:
            amount_text = f"{float(session.get('billed_amount', 0) or 0):.2f} €"
        except (TypeError, ValueError):
            amount_text = "0.00 €"

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Λεπτομέρειες Συνεδρίας #{session.get('id', '')}")
        dialog.setMinimumWidth(460)

        outer_layout = QVBoxLayout(dialog)

        info_group = QGroupBox("Στοιχεία Συνεδρίας")
        form = QFormLayout(info_group)
        form.addRow("Κωδικός:", QLabel(str(session.get('id', '-'))))
        form.addRow("Πελάτης:", QLabel(client_name))
        form.addRow("Τύπος:", QLabel(type_display))
        form.addRow("Κατάσταση:", QLabel(status_display))
        form.addRow("Έναρξη:", QLabel(fmt_datetime(session.get('start_time'))))
        form.addRow("Λήξη:", QLabel(fmt_datetime(session.get('end_time'))))
        form.addRow("Διάρκεια:", QLabel(duration_text))
        form.addRow("Τεχνικός:", QLabel(str(session.get('technician') or '-')))
        form.addRow("Χρέωση:", QLabel(amount_text))
        outer_layout.addWidget(info_group)

        # Description / issue notes (may be under different keys)
        description = (
            session.get('description')
            or session.get('issue_description')
            or session.get('issue_summary')
            or ''
        )
        if description:
            notes_group = QGroupBox("Περιγραφή / Σημειώσεις")
            notes_layout = QVBoxLayout(notes_group)
            notes_edit = QTextEdit()
            notes_edit.setPlainText(str(description))
            notes_edit.setReadOnly(True)
            notes_edit.setMaximumHeight(120)
            notes_layout.addWidget(notes_edit)
            outer_layout.addWidget(notes_group)

        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(dialog.reject)
        button_box.accepted.connect(dialog.accept)
        outer_layout.addWidget(button_box)

        dialog.exec()
