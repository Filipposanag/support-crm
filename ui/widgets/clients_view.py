# -*- coding: utf-8 -*-
"""
Clients View - Προβολή Πελατών
Main view for displaying and managing client records.
Κύρια προβολή για εμφάνιση και διαχείριση εγγραφών πελατών.
"""

import logging
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QCheckBox,
    QPushButton, QTableView, QLabel, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem

from db.repositories.clients_repo import ClientsRepository
from services.rustdesk_service import RustDeskService
from ui.i18n import TranslationManager
from resources.icons import get_icon
from ui.utils.permission_helper import has_permission

logger = logging.getLogger(__name__)


class ClientsView(QWidget):
    """
    Main view for clients management.
    Κύρια προβολή για διαχείριση πελατών.
    """
    
    # Signal emitted when a RustDesk session ends (to notify SessionsView)
    session_ended = Signal()
    
    def __init__(
        self,
        clients_repo: ClientsRepository,
        rustdesk_service: RustDeskService,
        tr_manager: TranslationManager,
        settings_service=None,
        session_service=None,
        parent=None
    ):
        """
        Initialize ClientsView.
        
        Args:
            clients_repo: ClientsRepository instance
            rustdesk_service: RustDeskService instance
            tr_manager: TranslationManager instance
            settings_service: SettingsService instance (optional)
            session_service: SessionService instance (optional)
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.clients_repo = clients_repo
        self.rustdesk_service = rustdesk_service
        self.tr_manager = tr_manager
        self.settings_service = settings_service
        self.session_service = session_service
        
        # Pagination state
        self.current_page = 0
        self.page_size = 50
        self.total_records = 0
        
        # Filter state
        self.search_text = ""
        self.only_active = True
        
        # Debounce timer for search
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(500)
        self.search_timer.timeout.connect(self._apply_filters)
        
        self._init_ui()
        self._connect_signals()
        
        # Initial load
        self.refresh()
        
        logger.debug("ClientsView initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel(self.tr_manager.get('clients'))
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)
        
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
    
    def _create_filter_bar(self) -> QHBoxLayout:
        """Create the filter bar with search and filters."""
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            self.tr_manager.get('search_placeholder')
        )
        self.search_input.setMinimumWidth(300)
        filter_layout.addWidget(self.search_input)
        
        # Active only checkbox
        self.active_only_checkbox = QCheckBox(
            self.tr_manager.get('show_active')
        )
        self.active_only_checkbox.setChecked(True)
        filter_layout.addWidget(self.active_only_checkbox)
        
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
        
        # New client button
        self.new_btn = QPushButton(
            get_icon('add'),
            self.tr_manager.get('new_client')
        )
        self.new_btn.setStyleSheet("QPushButton{background-color:#4CAF50;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#45a049;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        button_layout.addWidget(self.new_btn)
        
        # Edit client button
        self.edit_btn = QPushButton(
            get_icon('edit'),
            self.tr_manager.get('edit_client')
        )
        self.edit_btn.setEnabled(False)
        self.edit_btn.setStyleSheet("QPushButton{background-color:#F9A825;color:#212121;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#F57F17;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        button_layout.addWidget(self.edit_btn)
        
        # Client card button (blue)
        self.card_btn = QPushButton(
            get_icon('user'),
            "Καρτέλα Πελάτη"
        )
        self.card_btn.setEnabled(False)
        self.card_btn.setStyleSheet("QPushButton{background-color:#1976D2;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#1565C0;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        button_layout.addWidget(self.card_btn)
        
        # Delete client button
        self.delete_btn = QPushButton(
            get_icon('delete'),
            self.tr_manager.get('delete_client')
        )
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("QPushButton{background-color:#E53935;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#C62828;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        # Records count label
        self.records_label = QLabel()
        self._update_records_label()
        button_layout.addWidget(self.records_label)
        
        return button_layout
    
    def _setup_table_columns(self):
        """Setup table columns."""
        headers = [
            self.tr_manager.get('client_code').replace('_', ' '),
            self.tr_manager.get('last_name').replace('_', ' '),
            self.tr_manager.get('first_name').replace('_', ' '),
            self.tr_manager.get('company_name').replace('_', ' '),
            self.tr_manager.get('phone').replace('_', ' '),
            self.tr_manager.get('email').replace('_', ' '),
            self.tr_manager.get('city').replace('_', ' '),
            self.tr_manager.get('rustdesk_id').replace('_', ' '),
            self.tr_manager.get('support_plan').replace('_', ' '),
            self.tr_manager.get('active').replace('_', ' '),
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
        default_widths = [80, 120, 120, 150, 100, 150, 100, 120, 120, 80]
        
        header = self.table_view.horizontalHeader()
        for i, default_width in enumerate(default_widths):
            # Load saved width or use default
            width = settings.value(f'clients_view/column_{i}', default_width, type=int)
            header.resizeSection(i, width)
    
    def _on_column_resized(self, index, old_size, new_size):
        """Save column width when resized."""
        from PySide6.QtCore import QSettings
        settings = QSettings('SupportCRM', 'ColumnWidths')
        settings.setValue(f'clients_view/column_{index}', new_size)
    
    def _connect_signals(self):
        """Connect signals to slots."""
        # Search input
        self.search_input.textChanged.connect(self._on_search_changed)
        
        # Active only checkbox
        self.active_only_checkbox.stateChanged.connect(self._apply_filters)
        
        # Refresh button
        self.refresh_btn.clicked.connect(self.refresh)
        
        # Action buttons
        self.new_btn.clicked.connect(self._on_new_client)
        self.edit_btn.clicked.connect(self._on_edit_client)
        self.delete_btn.clicked.connect(self._on_delete_client)
        self.card_btn.clicked.connect(self._on_open_card)
        
        # Table selection
        self.table_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )
        
        # Double-click to edit
        self.table_view.doubleClicked.connect(self._on_open_card)
    
    def _on_search_changed(self, text: str):
        """Handle search text change with debounce."""
        self.search_text = text
        self.search_timer.start()
    
    def _apply_filters(self):
        """Apply current filters and refresh data."""
        self.current_page = 0
        self.refresh()
    
    def refresh(self):
        """Refresh the table data."""
        try:
            # Get filter values
            search = self.search_text.strip()
            only_active = self.active_only_checkbox.isChecked()
            
            # Calculate offset
            offset = self.current_page * self.page_size
            
            # Fetch data
            clients = self.clients_repo.list_clients(
                search=search if search else None,
                only_active=only_active,
                limit=self.page_size,
                offset=offset
            )
            
            # Get total count
            self.total_records = self.clients_repo.count_clients(
                search=search if search else None,
                only_active=only_active
            )
            
            # Update table
            self._populate_table(clients)
            
            # Update UI
            self._update_records_label()
            
            logger.debug(f"Refreshed clients view: {len(clients)} records")
            
        except Exception as e:
            logger.error(f"Error refreshing clients view: {e}")
            QMessageBox.critical(
                self,
                self.tr_manager.get('error'),
                f"Σφάλμα φόρτωσης δεδομένων: {str(e)}"
            )
    
    def _populate_table(self, clients: list):
        """Populate table with client data."""
        from PySide6.QtGui import QBrush, QColor
        
        self.table_model.removeRows(0, self.table_model.rowCount())
        
        try:
            active_pkg = self.clients_repo.get_active_package_names()
        except Exception:
            active_pkg = {}
        
        for client in clients:
            row = []
            
            # Code
            row.append(QStandardItem(str(client.get('legacy_code', ''))))
            
            # Last name
            row.append(QStandardItem(client.get('last_name', '')))
            
            # First name
            row.append(QStandardItem(client.get('first_name', '')))
            
            # Company name
            row.append(QStandardItem(client.get('company_name', '')))
            
            # Phone
            row.append(QStandardItem(client.get('phone', '')))
            
            # Email
            row.append(QStandardItem(client.get('email', '')))
            
            # City
            row.append(QStandardItem(client.get('city', '')))
            
            # RustDesk ID
            rustdesk_id = client.get('rustdesk_id', '')
            row.append(QStandardItem(rustdesk_id if rustdesk_id else '-'))
            
            # Support plan: δείξε το ΕΝΕΡΓΟ πακέτο αν υπάρχει, αλλιώς το πλάνο (Ωριαία κ.λπ.)
            _pkg_name = active_pkg.get(client.get('id'))
            if _pkg_name:
                plan_display = _pkg_name
            else:
                plan = client.get('support_plan', 'hourly')
                plan_display = {
                    'hourly': 'Ωριαία',
                    'monthly': 'Μηνιαία',
                    'yearly': 'Ετήσια',
                    'custom': 'Προσαρμοσμένο'
                }.get(plan, plan)
            row.append(QStandardItem(plan_display))
            
            # Active status with color coding
            is_active = client.get('is_active', 1)
            status_text = '● Ενεργός' if is_active else '● Ανενεργός'
            status_item = QStandardItem(status_text)
            
            # Set color based on status
            if is_active:
                status_item.setForeground(QBrush(QColor(76, 175, 80)))  # Green #4CAF50
            else:
                status_item.setForeground(QBrush(QColor(244, 67, 54)))  # Red #F44336
            
            row.append(status_item)
            
            # Store client ID in first column
            row[0].setData(client.get('id'), Qt.UserRole)
            
            self.table_model.appendRow(row)
    
    def _update_records_label(self):
        """Update the records count label."""
        start = self.current_page * self.page_size + 1
        end = min(start + self.page_size - 1, self.total_records)
        
        if self.total_records == 0:
            text = self.tr_manager.get('table_no_data')
        else:
            text = f"{self.tr_manager.get('total_clients')}: {self.total_records} ({start}-{end})"
        
        self.records_label.setText(text)
    
    def _on_selection_changed(self):
        """Handle table selection change."""
        has_selection = self.table_view.selectionModel().hasSelection()
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection and has_permission('clients.delete'))
        self.card_btn.setEnabled(has_selection)
    
    def _get_selected_client_id(self) -> Optional[int]:
        """Get the ID of the selected client."""
        selection = self.table_view.selectionModel().selectedRows()
        if not selection:
            return None
        
        index = selection[0]
        return self.table_model.item(index.row(), 0).data(Qt.UserRole)
    
    def _on_new_client(self):
        """Handle new client button click."""
        from ui.widgets.client_form import ClientForm
        
        dialog = ClientForm(
            clients_repo=self.clients_repo,
            tr_manager=self.tr_manager,
            parent=self
        )
        dialog.client_saved.connect(lambda: self.refresh())
        dialog.exec()
    
    def _on_open_card(self):
        """Open the 360° client card on double-click."""
        client_id = self._get_selected_client_id()
        if not client_id:
            return
        try:
            from ui.widgets.client_card_dialog import ClientCardDialog
            dlg = ClientCardDialog(client_id, self.clients_repo,
                                   self.rustdesk_service, self.tr_manager, self)
            dlg.exec()
            self.refresh()
        except Exception as e:
            logger.error(f"Failed to open client card: {e}", exc_info=True)

    def _on_edit_client(self):
        """Handle edit client button click."""
        client_id = self._get_selected_client_id()
        if not client_id:
            return
        
        from ui.widgets.client_form import ClientForm
        
        dialog = ClientForm(
            clients_repo=self.clients_repo,
            tr_manager=self.tr_manager,
            client_id=client_id,
            parent=self
        )
        dialog.client_saved.connect(lambda: self.refresh())
        dialog.session_ended.connect(self.session_ended)
        dialog.exec()
    
    def _on_delete_client(self):
        """Handle delete client button click."""
        if not has_permission('clients.delete'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα διαγραφής πελάτη.")
            return
        client_id = self._get_selected_client_id()
        if not client_id:
            return
        
        # Get client name for confirmation message
        try:
            client = self.clients_repo.get_client_by_id(client_id)
            if not client:
                return
            
            if client.get('company_name'):
                client_name = client['company_name']
            else:
                client_name = f"{client.get('last_name', '')} {client.get('first_name', '')}".strip()
        except:
            client_name = "αυτόν τον πελάτη"
        
        # Confirmation dialog with warning
        _dlg = QMessageBox(self)
        _dlg.setIcon(QMessageBox.Warning)
        _dlg.setWindowTitle("⚠️ Διαγραφή Πελάτη")
        _dlg.setText(
            f"Θέλετε να διαγράψετε τον πελάτη: {client_name}?\n\n"
            f"⚠️ ΠΡΟΣΟΧΗ: Θα διαγραφούν ΟΡΙΣΤΙΚΑ:\n"
            f"   • Ο πελάτης\n"
            f"   • Όλες οι πληρωμές\n"
            f"   • Όλες οι συνδρομές\n"
            f"   • Όλες οι συνεδρίες\n"
            f"   • Όλα τα μέλη\n"
            f"   • Όλες οι προπληρωμένες ώρες\n\n"
            f"Αυτή η ενέργεια ΔΕΝ μπορεί να αναιρεθεί!"
        )
        _dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        _dlg.button(QMessageBox.Yes).setText("Ναι")
        _dlg.button(QMessageBox.No).setText("Όχι")
        _dlg.setDefaultButton(QMessageBox.No)
        reply = _dlg.exec()
        
        if reply == QMessageBox.Yes:
            try:
                # Use permanent delete instead of soft delete
                self.clients_repo.delete_client(client_id)
                QMessageBox.information(
                    self,
                    self.tr_manager.get('success'),
                    f"Ο πελάτης και όλα τα σχετικά δεδομένα διαγράφηκαν επιτυχώς."
                )
                self.refresh()
            except Exception as e:
                logger.error(f"Error deleting client: {e}")
                QMessageBox.critical(
                    self,
                    self.tr_manager.get('error'),
                    f"Σφάλμα διαγραφής πελάτη:\n{str(e)}"
                )
    
    def _on_connect_rustdesk(self):
        """Handle RustDesk connect button click."""
        client_id = self._get_selected_client_id()
        if not client_id:
            return
        
        try:
            # Get client data
            client = self.clients_repo.get_client_by_id(client_id)
            if not client:
                return
            
            rustdesk_id = client.get('rustdesk_id', '').strip()
            rustdesk_password = client.get('rustdesk_password', '').strip()
            
            if not rustdesk_id:
                QMessageBox.warning(
                    self,
                    "RustDesk ID Απαιτείται",
                    "Ο πελάτης δεν έχει RustDesk ID.\n\n"
                    "Παρακαλώ προσθέστε το RustDesk ID στα στοιχεία του πελάτη."
                )
                return
            
            # Load RustDesk settings from database
            if self.settings_service:
                settings = self.settings_service.load_settings()
                if settings and settings.rustdesk_server_host:
                    self.rustdesk_service.configure_server(
                        host=settings.rustdesk_server_host,
                        port=settings.rustdesk_server_port,
                        api_key=settings.rustdesk_api_key
                    )
            
            # Check if RustDesk is available
            if not self.rustdesk_service.is_available():
                QMessageBox.warning(
                    self,
                    "RustDesk Μη Διαθέσιμο",
                    "Το RustDesk δεν βρέθηκε στο σύστημα.\n\n"
                    "Παρακαλώ εγκαταστήστε το RustDesk από:\n"
                    "https://rustdesk.com/"
                )
                return
            
            # Connect
            success = self.rustdesk_service.connect_to_client(
                rustdesk_id,
                rustdesk_password if rustdesk_password else None
            )
            
            if success:
                client_name = client.get('company_name') or f"{client.get('last_name', '')} {client.get('first_name', '')}".strip()
                
                # Auto-start session for this client
                session_started = False
                if self.session_service:
                    try:
                        # Start session directly using session_service
                        session_id = self.session_service.start_session(
                            client_id=client_id,
                            session_type='remote',
                            technician="",  # Will be filled later
                            description=f"Απομακρυσμένη υποστήριξη μέσω RustDesk - {client_name}"
                        )
                        
                        if session_id:
                            session_started = True
                            logger.info(f"Auto-started session {session_id} for client {client_id}")
                            
                            # Try to refresh sessions view if it's loaded
                            main_window = self.window()
                            if hasattr(main_window, '_views') and 'sessions' in main_window._views:
                                sessions_view = main_window._views['sessions']
                                sessions_view.refresh()
                                logger.debug("Refreshed sessions view")
                        else:
                            logger.warning("Failed to start session")
                    except Exception as e:
                        logger.error(f"Error auto-starting session: {e}", exc_info=True)
                else:
                    logger.warning("session_service not available - cannot auto-start session")
                
                # Show success message
                message = (
                    f"Η σύνδεση RustDesk ξεκίνησε!\n\n"
                    f"Πελάτης: {client_name}\n"
                    f"RustDesk ID: {rustdesk_id}\n\n"
                    f"Το RustDesk θα ανοίξει σε λίγο.\n"
                )
                
                if session_started:
                    message += f"✅ Ένα session ξεκίνησε αυτόματα για καταγραφή του χρόνου."
                else:
                    message += f"⚠️ Παρακαλώ ξεκινήστε ένα session manually από το tab Συνεδρίες."
                
                QMessageBox.information(
                    self,
                    "Σύνδεση Ξεκίνησε",
                    message
                )
                logger.info(f"RustDesk connection initiated to client {client_id} ({rustdesk_id})")
            else:
                QMessageBox.warning(
                    self,
                    "Αποτυχία Σύνδεσης",
                    "Αποτυχία εκκίνησης σύνδεσης RustDesk.\n\n"
                    "Ελέγξτε τα logs για περισσότερες πληροφορίες."
                )
                
        except Exception as e:
            logger.error(f"Error connecting to RustDesk: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                self.tr_manager.get('error'),
                f"Σφάλμα σύνδεσης RustDesk:\n{str(e)}"
            )
