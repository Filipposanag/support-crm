# -*- coding: utf-8 -*-
"""
Main application window for Support CRM.
Provides navigation, view management, and application-level UI components.
"""

import logging
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict
import config
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget,
    QMenuBar, QMenu, QStatusBar, QLabel, QComboBox,
    QMessageBox, QSplitter, QApplication, QProgressDialog, QDialog
)
from PySide6.QtCore import Qt, Signal, QTimer, QSettings
from PySide6.QtGui import QAction, QIcon, QColor

from ui.i18n import TranslationManager, get_translation_manager
from db.connection import DatabaseConnection
from db.repositories.families_repo import FamiliesRepository
from db.repositories.members_repo import MembersRepository
from db.repositories.payments_repo import PaymentsRepository
from db.repositories.imports_repo import ImportsRepository
from services.import_service import ImportService
from services.reporting_service import ReportingService
from services.settings_service import SettingsService
from services.receipt_service import ReceiptService
from resources.icons import get_icon
from ui.utils.permission_helper import has_permission
from utils.resource_loader import app_icon, main_logo

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window with navigation sidebar and view management.
    
    Provides:
    - Menu bar with File, Edit, View, Tools, Help menus
    - Sidebar navigation for Families, Payments, Import, Reports
    - Central stacked widget for view switching
    - Status bar with connection status and language selector
    """
    
    # Signal emitted when language changes
    language_changed = Signal(str)
    
    def __init__(self, db_connection: DatabaseConnection, auth_service=None, parent: Optional[QWidget] = None):
        """
        Initialize the main window.
        
        Args:
            db_connection: Database connection instance
            auth_service: AuthService instance for user authentication (optional)
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        
        self.db_connection = db_connection
        self.auth_service = auth_service
        self.tr_manager = get_translation_manager()
        
        # Initialize repositories
        self.families_repo = FamiliesRepository(db_connection)
        self.members_repo = MembersRepository(db_connection)
        self.payments_repo = PaymentsRepository(db_connection)
        self.imports_repo = ImportsRepository(db_connection)
        
        # Support CRM - New repositories
        from db.repositories.clients_repo import ClientsRepository
        from db.repositories.sessions_repo import SessionsRepository
        self.clients_repo = ClientsRepository(db_connection)
        self.sessions_repo = SessionsRepository(db_connection)
        
        # Initialize services
        self.import_service = ImportService(
            self.families_repo,
            self.members_repo,
            self.payments_repo,
            self.imports_repo
        )
        self.reporting_service = ReportingService(
            self.families_repo,
            self.payments_repo
        )
        self.settings_service = SettingsService(db_connection)
        self.receipt_service = ReceiptService(
            self.payments_repo,
            self.settings_service
        )
        self.maintenance_service = None  # Will be initialized lazily
        
        # Inject reporting_service into repositories for cache invalidation
        self.families_repo.reporting_service = self.reporting_service
        self.payments_repo.reporting_service = self.reporting_service
        
        # View cache for lazy loading
        self._views: Dict[str, QWidget] = {}
        
        # Initialize settings for user preferences
        self.settings = QSettings('SupportCRM', 'SupportCRM')
        
        # Initialize UI components
        self._init_ui()
        self._create_menu_bar()
        self._create_status_bar()
        self._setup_connections()
        
        # Restore user preferences
        self._restore_preferences()
        
        # Load initial view (Families)
        QTimer.singleShot(50, self._load_initial_view)
        
        # Check database connection on startup
        QTimer.singleShot(100, self._check_database_connection)
        
        # Automatic daily database backup into the backups folder (once per day)
        QTimer.singleShot(1500, self._auto_backup_if_needed)
        
        logger.info("MainWindow initialized")
    
    def _auto_backup_if_needed(self):
        """Create one automatic database backup per day, saved in the backups folder."""
        try:
            from services.backup_service import BackupService
            svc = BackupService(self.db_connection.config)
            if svc.has_backup_today():
                logger.debug("Automatic backup already exists for today; skipping")
                return
            path = svc.auto_backup(max_keep=30)
            if path:
                logger.info(f"Automatic daily backup saved: {path}")
            else:
                logger.warning("Automatic daily backup did not complete (DB tools missing?)")
        except Exception as e:
            logger.error(f"Automatic backup check failed: {e}", exc_info=True)

    def _init_ui(self):
        """Initialize the user interface layout and components."""
        # Set window properties
        self.setWindowTitle(self.tr_manager.get('app_title'))
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1024, 768)
        self.resize(1280, 800)
        
        # Create central widget with splitter layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for resizable sidebar
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Create sidebar navigation
        self.sidebar = self._create_sidebar()
        splitter.addWidget(self.sidebar)
        
        # Create central stacked widget for views
        self.stacked_widget = QStackedWidget()
        splitter.addWidget(self.stacked_widget)
        
        # Set splitter proportions (sidebar: 200px, content: rest)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 1080])
        
        logger.debug("UI layout initialized")
    
    def _create_sidebar(self) -> QWidget:
        """
        Create the navigation sidebar with list of views.
        
        Returns:
            Sidebar widget containing navigation list
        """
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(5, 5, 5, 5)
        sidebar_layout.setSpacing(10)
        
        # Add logo at the top
        logo_label = QLabel()
        logo_pixmap = main_logo(width=180)
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("padding: 10px;")
        sidebar_layout.addWidget(logo_label)
        
        # Create navigation list
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navigationList")
        
        # Grouped navigation with section headers
        _is_admin = bool(self.auth_service and self.auth_service.current_user
                         and self.auth_service.current_user.username == 'admin')
        # System section is admin-only (Χρήστες / Ιστορικό κινήσεων / Ρυθμίσεις)
        _system_items = []
        if _is_admin:
            _system_items = [('nav_tech_performance', 'tech_performance', 'reports'),
                             ('nav_users', 'users', 'user'),
                             ('nav_audit_log', 'audit_log', 'audit_log'),
                             ('nav_settings', 'settings', 'settings')]
        _NAV_PERMS = {'client_packages': 'packages.expirations'}
        nav_groups = [
            ("ΕΠΙΣΚΟΠΗΣΗ", [('nav_dashboard', 'dashboard', 'reports')]),
            ("ΠΕΛΑΤΕΣ", [('nav_clients', 'clients', 'families')]),
            ("ΥΠΟΣΤΗΡΙΞΗ", [('nav_sessions', 'sessions', 'subscriptions')]),
            ("ΟΙΚΟΝΟΜΙΚΑ", [
                ('nav_payments', 'payments', 'payments'),
                ('nav_documents', 'documents', 'export'),
                ('nav_packages', 'packages', 'package'),
                ('nav_expiring', 'client_packages', 'subscriptions'),
                ('nav_debts', 'debts', 'payments'),
            ]),
            ("ΑΝΑΛΥΣΗ", [('nav_reports', 'reports', 'reports')]),
            ("ΣΥΣΤΗΜΑ", _system_items),
        ]

        first_real_row = -1
        for title, items in nav_groups:
            if not items:
                continue  # hide empty sections (e.g. ΣΥΣΤΗΜΑ for non-admins)
            header = QListWidgetItem(title)
            header.setFlags(Qt.NoItemFlags)  # non-selectable section label
            hf = header.font()
            hf.setBold(True)
            hf.setPointSize(max(7, hf.pointSize() - 1))
            header.setFont(hf)
            header.setForeground(QColor(0x90, 0x9C, 0xAA))
            self.nav_list.addItem(header)
            for text_key, view_id, icon_name in items:
                _req = _NAV_PERMS.get(view_id)
                if _req and not has_permission(_req):
                    continue  # hide nav items the user has no permission for
                item = QListWidgetItem(get_icon(icon_name), "  " + self.tr_manager.get(text_key))
                item.setData(Qt.UserRole, view_id)
                self.nav_list.addItem(item)
                if first_real_row < 0:
                    first_real_row = self.nav_list.count() - 1

        # Select first real (non-header) item by default
        self.nav_list.setCurrentRow(first_real_row if first_real_row >= 0 else 0)
        
        sidebar_layout.addWidget(self.nav_list)
        
        logger.debug("Sidebar navigation created with logo")
        return sidebar_widget
    
    def _create_menu_bar(self):
        """Create the application menu bar with all menus."""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu(self.tr_manager.get('menu_file'))
        
        exit_action = QAction(get_icon('delete'), self.tr_manager.get('menu_exit'), self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu — only shown when it would have content (settings access)
        if has_permission('settings.view'):
            edit_menu = menubar.addMenu(self.tr_manager.get('menu_edit'))
            preferences_action = QAction(get_icon('settings'), self.tr_manager.get('menu_preferences'), self)
            preferences_action.triggered.connect(self._show_preferences)
            edit_menu.addAction(preferences_action)
        
        # View Menu
        view_menu = menubar.addMenu(self.tr_manager.get('menu_view'))
        
        refresh_action = QAction(get_icon('refresh'), self.tr_manager.get('menu_refresh'), self)
        refresh_action.setShortcut('F5')
        refresh_action.triggered.connect(self._refresh_current_view)
        view_menu.addAction(refresh_action)
        
        # Tools Menu — admin-only (Εισαγωγή δεδομένων + Ρυθμίσεις βάσης)
        _is_admin = bool(self.auth_service and self.auth_service.current_user
                         and self.auth_service.current_user.username == 'admin')
        if _is_admin:
            tools_menu = menubar.addMenu(self.tr_manager.get('menu_tools'))

            import_csv_action = QAction(get_icon('import'), self.tr_manager.get('menu_import_data'), self)
            import_csv_action.triggered.connect(self._show_import_dialog)
            tools_menu.addAction(import_csv_action)

            tools_menu.addSeparator()

            db_config_action = QAction(get_icon('settings'), "Ρυθμίσεις βάσης δεδομένων...", self)
            db_config_action.triggered.connect(self._open_db_configurator)
            tools_menu.addAction(db_config_action)
        
        # Help Menu
        help_menu = menubar.addMenu(self.tr_manager.get('menu_help'))
        
        # Check for updates action
        check_updates_action = QAction("Έλεγχος για ενημερώσεις", self)
        check_updates_action.triggered.connect(self._check_for_updates)
        help_menu.addAction(check_updates_action)
        
        help_menu.addSeparator()
        
        about_action = QAction(self.tr_manager.get('menu_about'), self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        logger.debug("Menu bar created")
    
    def _create_status_bar(self):
        """Create the status bar with connection status and language selector."""
        statusbar = self.statusBar()
        
        # Connection status label
        self.connection_status_label = QLabel()
        self._update_connection_status(False)  # Initially disconnected
        statusbar.addPermanentWidget(self.connection_status_label)
        
        # Separator
        separator = QLabel(" | ")
        statusbar.addPermanentWidget(separator)
        
        # License status label (clickable)
        self.license_status_label = QLabel()
        self.license_status_label.setStyleSheet("padding: 4px 8px; border-radius: 3px;")
        self.license_status_label.mousePressEvent = lambda event: self._open_license_settings()
        self.license_status_label.setToolTip("Κλικ για ρυθμίσεις άδειας")
        self._update_license_status()
        statusbar.addPermanentWidget(self.license_status_label)
        
        # Set default status message
        statusbar.showMessage(self.tr_manager.get('status_ready'))
        
        logger.debug("Status bar created")
    
    def _setup_connections(self):
        """Setup signal-slot connections."""
        # Navigation list selection
        self.nav_list.currentRowChanged.connect(self._on_navigation_changed)
        
        logger.debug("Signal connections established")
    
    def _load_initial_view(self):
        """Load the initial view (Clients) on startup."""
        try:
            # Get the first navigation item (Clients)
            for _i in range(self.nav_list.count()):
                _it = self.nav_list.item(_i)
                if _it and _it.data(Qt.UserRole):
                    self._switch_to_view(_it.data(Qt.UserRole))
                    logger.debug(f"Initial view loaded: {_it.data(Qt.UserRole)}")
                    break
        except Exception as e:
            logger.error(f"Error loading initial view: {e}", exc_info=True)
    
    def _on_navigation_changed(self, index: int):
        """
        Handle navigation list selection change.
        
        Args:
            index: Selected row index
        """
        if index < 0:
            return
        
        item = self.nav_list.item(index)
        if not item:
            return
        
        view_id = item.data(Qt.UserRole)
        if not view_id:
            return  # header row, ignore
        self._switch_to_view(view_id)
        
        logger.debug(f"Navigation changed to: {view_id}")
    
    def _switch_to_view(self, view_id: str):
        """
        Switch to the specified view (lazy loading).
        Ensures view switching completes within 100ms for cached views.
        
        Args:
            view_id: Identifier of the view to switch to
        """
        try:
            import time
            start_time = time.time()
            
            # Check if view is already loaded (fast path - should be < 100ms)
            if view_id in self._views:
                view = self._views[view_id]
                self.stacked_widget.setCurrentWidget(view)
                for _m in ('refresh', 'load', 'reload'):
                    if hasattr(view, _m):
                        try:
                            getattr(view, _m)()
                        except Exception as _e:
                            logger.debug(f"view refresh skipped: {_e}")
                        break
                elapsed = (time.time() - start_time) * 1000
                logger.debug(f"Switched to cached view: {view_id} in {elapsed:.2f}ms")
                return
            
            # Load view on demand (first time only)
            view = self._create_view(view_id)
            if view:
                self._views[view_id] = view
                self.stacked_widget.addWidget(view)
                self.stacked_widget.setCurrentWidget(view)
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"Loaded and switched to new view: {view_id} in {elapsed:.2f}ms")
            else:
                logger.warning(f"Failed to create view: {view_id}")
                
        except Exception as e:
            logger.error(f"Error switching to view '{view_id}': {e}", exc_info=True)
            QMessageBox.critical(
                self,
                self.tr_manager.get('error_title'),
                f"{self.tr_manager.get('error_view_switch')}: {view_id}\n\n{str(e)}"
            )
    
    def _on_open_expirations(self):
        """From the dashboard 'Πακέτα που λήγουν' section: open the Λήξεις screen."""
        if not has_permission('packages.expirations'):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                                "Δεν έχετε δικαίωμα πρόσβασης στις Λήξεις Πακέτων.")
            return
        try:
            for i in range(self.nav_list.count()):
                it = self.nav_list.item(i)
                if it and it.data(Qt.UserRole) == 'client_packages':
                    self.nav_list.setCurrentRow(i)
                    return
            self._switch_to_view('client_packages')
        except Exception as e:
            logger.error(f"open expirations failed: {e}")

    def _on_open_client_in_debts(self, client_id):
        """From the dashboard alerts panel: switch to the Οφειλές screen and
        open the selected client's card."""
        try:
            target_row = None
            for i in range(self.nav_list.count()):
                it = self.nav_list.item(i)
                if it and it.data(Qt.UserRole) == 'debts':
                    target_row = i
                    break
            if target_row is not None:
                self.nav_list.setCurrentRow(target_row)
            else:
                self._switch_to_view('debts')
            debts_view = self._views.get('debts')
            if debts_view is not None and hasattr(debts_view, 'open_client_card'):
                debts_view.open_client_card(int(client_id))
        except Exception as e:
            logger.error(f"Failed to open client in debts: {e}", exc_info=True)

    def _create_view(self, view_id: str) -> Optional[QWidget]:
        """
        Create a view widget based on view ID.
        
        Args:
            view_id: Identifier of the view to create
            
        Returns:
            View widget or None if view type is unknown
        """
        try:
            if view_id == 'dashboard':
                from ui.widgets.dashboard_view import DashboardView
                view = DashboardView(self.db_connection, self.tr_manager, self)
                view.open_client_in_debts.connect(self._on_open_client_in_debts)
                view.open_expirations.connect(self._on_open_expirations)
                logger.debug("Created DashboardView")
                return view

            if view_id == 'tech_performance':
                from ui.widgets.tech_performance_view import TechPerformanceView
                logger.debug("Created TechPerformanceView")
                return TechPerformanceView(self.db_connection, self.tr_manager, self)

            # Support CRM - New views
            if view_id == 'clients':
                from ui.widgets.clients_view import ClientsView
                from services.rustdesk_service import RustDeskService
                from services.session_service import SessionService
                
                # Initialize RustDesk service
                rustdesk_service = RustDeskService()
                
                # Initialize session service for auto-start
                session_service = SessionService(self.db_connection)
                
                view = ClientsView(
                    self.clients_repo,
                    rustdesk_service,
                    self.tr_manager,
                    self.settings_service,
                    session_service,
                    self
                )
                
                # When RustDesk session ends, auto-refresh SessionsView if loaded
                view.session_ended.connect(self._on_session_ended_from_rustdesk)
                
                logger.debug(f"Created ClientsView")
                return view
            
            elif view_id == 'sessions':
                from ui.widgets.sessions_view import SessionsView
                from services.session_service import SessionService
                from services.rustdesk_service import RustDeskService
                
                # Initialize session service
                session_service = SessionService(self.db_connection)
                
                # Initialize RustDesk service
                rustdesk_service = RustDeskService()
                
                view = SessionsView(
                    self.sessions_repo,
                    self.clients_repo,
                    session_service,
                    self.tr_manager,
                    rustdesk_service,
                    self
                )
                logger.debug(f"Created SessionsView")
                return view
            

            elif view_id == 'debts':
                from ui.widgets.debts_view import DebtsView
                from services.rustdesk_service import RustDeskService
                view = DebtsView(
                    self.db_connection,
                    self.families_repo,
                    self.clients_repo,
                    RustDeskService(),
                    self.tr_manager,
                    self,
                )
                logger.debug("Created DebtsView")
                return view

            elif view_id == 'payments':
                from ui.widgets.payments_view import PaymentsView
                view = PaymentsView(
                    self.payments_repo,
                    self.families_repo,
                    self.receipt_service,
                    self.settings_service,
                    self.db_connection,
                    self
                )
                # Connect signal to refresh subscriptions view when payment changes
                view.payment_changed.connect(self._on_payment_changed)
                logger.debug(f"Created PaymentsView")
                return view

            elif view_id == 'documents':
                from ui.widgets.documents_view import DocumentsView
                view = DocumentsView(self.db_connection, self.clients_repo, self.tr_manager, self)
                logger.debug("Created DocumentsView")
                return view

            elif view_id == 'packages':
                from ui.widgets.packages_view import PackagesView
                view = PackagesView(self.db_connection, self)
                logger.debug("Created PackagesView")
                return view

            elif view_id == 'client_packages':
                from ui.widgets.client_packages_view import ClientPackagesView
                view = ClientPackagesView(self.db_connection, self.settings_service, self.receipt_service, self)
                logger.debug("Created ClientPackagesView")
                return view
            
            # Subscriptions view removed - subscriptions are now managed through payments
            # elif view_id == 'subscriptions':
            #     from ui.widgets.subscriptions_view import SubscriptionsView
            #     view = SubscriptionsView(...)
            #     return view
            
            elif view_id == 'reports':
                from ui.widgets.reports_view import ReportsView
                view = ReportsView(self.db_connection, self.tr_manager, self)
                logger.debug("Created ReportsView")
                return view
            
            elif view_id == 'audit_log':
                from ui.widgets.audit_log_view import AuditLogView
                from db.repositories.audit_log_repo import AuditLogRepository
                
                audit_log_repo = AuditLogRepository(self.db_connection)
                view = AuditLogView(audit_log_repo, self)
                logger.debug(f"Created AuditLogView")
                return view

            elif view_id == 'users':
                from ui.widgets.users_view import UsersView
                view = UsersView(self.db_connection, self)
                logger.debug("Created UsersView")
                return view
            
            elif view_id == 'settings':
                from ui.widgets.settings_view import SettingsView
                
                # Initialize maintenance service if not already done
                if not self.maintenance_service:
                    from services.maintenance_service import MaintenanceService
                    self.maintenance_service = MaintenanceService(self.db_connection)
                
                view = SettingsView(
                    self.settings_service,
                    self.tr_manager,
                    self.maintenance_service,
                    self.auth_service,  # Pass auth_service for user management
                    self
                )
                logger.debug(f"Created SettingsView")
                return view
            
            # All navigation views (clients, sessions, payments, reports,
            # audit_log, settings) are handled above. An unknown view_id is
            # not expected; log it and return None so the caller can handle it.
            logger.warning(f"No view defined for view_id: {view_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error creating view '{view_id}': {e}", exc_info=True)
            QMessageBox.critical(
                self,
                self.tr_manager.get('error_title'),
                f"{self.tr_manager.get('error_view_creation')}: {view_id}\n\n{str(e)}"
            )
            return None
    
    def _on_language_changed(self, index: int):
        """
        Handle language selector change.
        
        Args:
            index: Selected combo box index
        """
        # Language selection moved to configurator
        pass
    
    def _update_ui_text(self):
        """Update all UI text elements with current language translations."""
        # Update window title
        self.setWindowTitle(self.tr_manager.get('app_title'))
        
        # Update menu bar
        menus = self.menuBar().findChildren(QMenu)
        menu_keys = ['menu_file', 'menu_edit', 'menu_view', 'menu_tools', 'menu_help']
        for menu, key in zip(menus, menu_keys):
            menu.setTitle(self.tr_manager.get(key))
        
        # Update menu actions
        for action in self.menuBar().actions():
            menu = action.menu()
            if menu:
                for menu_action in menu.actions():
                    # Update action text based on its current text
                    text = menu_action.text()
                    # This is a simplified approach - in production, you'd store action keys
                    if 'Exit' in text or 'Έξοδος' in text:
                        menu_action.setText(self.tr_manager.get('menu_exit'))
                    elif 'Preferences' in text or 'Προτιμήσεις' in text:
                        menu_action.setText(self.tr_manager.get('menu_preferences'))
                    elif 'Refresh' in text or 'Ανανέωση' in text:
                        menu_action.setText(self.tr_manager.get('menu_refresh'))
                    elif 'About' in text or 'Σχετικά' in text:
                        menu_action.setText(self.tr_manager.get('menu_about'))
        
        # Update navigation items
        nav_items = ['nav_clients', 'nav_sessions', 'nav_payments', 'nav_reports', 'nav_audit_log', 'nav_settings']
        for i, key in enumerate(nav_items):
            item = self.nav_list.item(i)
            if item:
                item.setText(self.tr_manager.get(key))
        
        # Update status bar language label
        for widget in self.statusBar().findChildren(QLabel):
            if 'Language' in widget.text() or 'Γλώσσα' in widget.text():
                widget.setText(self.tr_manager.get('language') + ": ")
        
        # Update status bar message
        self.statusBar().showMessage(self.tr_manager.get('status_ready'))
        
        # Update connection status
        is_connected = self.db_connection.test_connection()
        self._update_connection_status(is_connected)
        
        # Notify all loaded views about language change
        for view_id, view in self._views.items():
            if hasattr(view, 'update_translations'):
                view.update_translations()
                logger.debug(f"Updated translations for view: {view_id}")
        
        logger.debug("UI text updated for language change")
    
    def _check_database_connection(self):
        """
        Check database connection status on startup.
        If connection fails, show error and close application.
        """
        try:
            is_connected = self.db_connection.test_connection()
            self._update_connection_status(is_connected)
            
            if not is_connected:
                self._show_connection_error()
                logger.error("Database connection failed on startup - closing application")
                # Close application if connection fails
                QTimer.singleShot(100, self.close)
        except Exception as e:
            self._update_connection_status(False)
            self._show_connection_error(str(e))
            logger.error(f"Database connection check failed: {e} - closing application")
            # Close application if connection check fails
            QTimer.singleShot(100, self.close)
    
    def _update_connection_status(self, is_connected: bool):
        """
        Update the connection status indicator in status bar.
        
        Args:
            is_connected: True if connected, False otherwise
        """
        if is_connected:
            status_text = self.tr_manager.get('status_connected')
            status_color = "#4CAF50"  # Green
        else:
            status_text = self.tr_manager.get('status_disconnected')
            status_color = "#F44336"  # Red
        
        self.connection_status_label.setText(f"● {status_text}")
        self.connection_status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
    
    def _update_license_status(self):
        """Update the license status indicator in status bar."""
        try:
            from services.license_service import LicenseService
            from datetime import datetime
            
            license_info = self.settings_service.get_license_info()
            
            if not license_info or license_info['status'] == 'none':
                self.license_status_label.setText("Άδεια: Δεν έχει οριστεί")
                self.license_status_label.setStyleSheet(
                    "padding: 4px 8px; border-radius: 3px; "
                    "background-color: #f5f5f5; color: #757575;"
                )
                return
            
            end_date = license_info['end_date']
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            days_remaining = LicenseService.calculate_days_remaining(end_date)
            status_text = LicenseService.get_license_status_text(license_info['status'], days_remaining)
            status_color = LicenseService.get_license_status_color(license_info['status'], days_remaining)
            
            # Format display text
            if license_info['status'] == 'expired' or days_remaining <= 0:
                display_text = f"Άδεια: Έληξε ({end_date.strftime('%d/%m/%Y')})"
            else:
                display_text = f"Άδεια: Ενεργή (λήξη: {end_date.strftime('%d/%m/%Y')})"
            
            self.license_status_label.setText(display_text)
            self.license_status_label.setStyleSheet(
                f"padding: 4px 8px; border-radius: 3px; "
                f"background-color: {status_color}; color: white; font-weight: bold;"
            )
            
        except Exception as e:
            logger.error(f"Failed to update license status: {e}")
            self.license_status_label.setText("Άδεια: Σφάλμα")
            self.license_status_label.setStyleSheet(
                "padding: 4px 8px; border-radius: 3px; "
                "background-color: #f5f5f5; color: #757575;"
            )
    
    def _open_license_settings(self):
        """Open license info dialog."""
        try:
            from ui.widgets.license_info_dialog import LicenseInfoDialog
            
            # Create and show license dialog
            dialog = LicenseInfoDialog(self.settings_service, self)
            dialog.exec()
            
            # Refresh license status after dialog closes
            self._update_license_status()
            
        except Exception as e:
            logger.error(f"Failed to open license dialog: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Αποτυχία ανοίγματος διαλόγου άδειας:\n{str(e)}"
            )
    
    def _show_connection_error(self, error_message: str = ""):
        """
        Show error dialog for database connection failure.
        Application will close after this dialog is dismissed.
        
        Args:
            error_message: Optional error message to display
        """
        title = self.tr_manager.get('error_title')
        message = self.tr_manager.get('error_database_connection')
        
        if error_message:
            message += f"\n\n{error_message}"
        
        # Add information about application closure
        message += f"\n\n{self.tr_manager.get('info_please_wait')}"
        message += "\nThe application will close."
        
        QMessageBox.critical(self, title, message)
        logger.error(f"Connection error dialog shown: {error_message}")
    
    def _refresh_current_view(self):
        """Refresh the currently active view."""
        current_widget = self.stacked_widget.currentWidget()
        if current_widget and hasattr(current_widget, 'refresh'):
            current_widget.refresh()
            logger.debug("Current view refreshed")
        else:
            logger.debug("Current view does not support refresh")
    
    def _on_payment_changed(self):
        """Handle payment changes."""
        logger.debug("Payment changed - subscriptions view no longer exists")
    
    def _on_session_ended_from_rustdesk(self):
        """Auto-refresh SessionsView when a RustDesk session ends."""
        sessions_view = self._views.get('sessions')
        if sessions_view and hasattr(sessions_view, 'refresh'):
            sessions_view.refresh()
            logger.info("SessionsView auto-refreshed after RustDesk session ended")
    
    def _on_subscription_payment_changed(self):
        """
        Handle payment changes from subscriptions view.
        Note: Subscriptions view has been removed - subscriptions are now managed through payments.
        """
        # Subscriptions view removed - no longer needed
        logger.debug("Subscription payment changed - subscriptions view no longer exists")
    
    def _show_import_dialog(self):
        """Show CSV import dialog."""
        # Admin-only guard
        if not (self.auth_service and self.auth_service.current_user
                and self.auth_service.current_user.username == 'admin'):
            QMessageBox.warning(self, "Πρόσβαση", "Αυτή η ενέργεια επιτρέπεται μόνο στον διαχειριστή.")
            return
        try:
            from ui.widgets.import_dialog import ImportDialog
            
            dialog = ImportDialog(
                self.import_service,
                self.tr_manager,
                self
            )
            dialog.exec()
            
            logger.debug("Import dialog closed")
            
        except Exception as e:
            logger.error(f"Error showing import dialog: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                self.tr_manager.get('error_title'),
                f"Σφάλμα κατά το άνοιγμα του εργαλείου εισαγωγής:\n\n{str(e)}"
            )
    
    def _show_subscription_email_tool(self):
        """Show subscription email tool dialog."""
        try:
            from ui.widgets.subscription_email_tool_dialog import SubscriptionEmailToolDialog
            from services.subscription_service import SubscriptionService
            from services.email_service import EmailService
            
            # Initialize services
            subscription_service = SubscriptionService(
                self.payments_repo,
                self.families_repo
            )
            email_service = EmailService(self.settings_service)
            
            # Show dialog
            dialog = SubscriptionEmailToolDialog(
                subscription_service,
                email_service,
                self.settings_service,
                self
            )
            dialog.exec()
            
            logger.debug("Subscription email tool dialog closed")
            
        except Exception as e:
            logger.error(f"Error showing subscription email tool: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά το άνοιγμα του εργαλείου αποστολής email:\n\n{str(e)}"
            )
    
    def _open_db_configurator(self):
        """Open database configurator dialog (embedded in main app)."""
        # Admin-only guard
        if not (self.auth_service and self.auth_service.current_user
                and self.auth_service.current_user.username == 'admin'):
            QMessageBox.warning(self, "Πρόσβαση", "Αυτή η ενέργεια επιτρέπεται μόνο στον διαχειριστή.")
            return
        try:
            # Import and open configurator dialog
            from configurator.db_configurator_window import DBConfiguratorWindow
            
            configurator = DBConfiguratorWindow(self)
            configurator.exec()  # Modal dialog
            
            logger.info("Database configurator dialog opened")
            
        except Exception as e:
            logger.error(f"Error opening DB configurator: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Αποτυχία ανοίγματος του configurator:\n\n{str(e)}"
            )
    
    def _show_preferences(self):
        """Show preferences dialog."""
        if not has_permission('settings.view'):
            return
        try:
            from ui.widgets.preferences_dialog import PreferencesDialog
            
            dialog = PreferencesDialog(self.settings_service, self)
            
            if dialog.exec_():
                # Preferences were saved, apply to all views
                logger.info("Applying column preferences to all views")
                
                # Apply to families view if loaded
                if 'families' in self._views:
                    families_view = self._views['families']
                    if hasattr(families_view, 'apply_column_preferences'):
                        families_view.apply_column_preferences()
                
                # Apply to payments view if loaded
                if 'payments' in self._views:
                    payments_view = self._views['payments']
                    if hasattr(payments_view, 'apply_column_preferences'):
                        payments_view.apply_column_preferences()
                
                # Apply to subscriptions view if loaded
                if 'subscriptions' in self._views:
                    subscriptions_view = self._views['subscriptions']
                    if hasattr(subscriptions_view, 'apply_column_preferences'):
                        subscriptions_view.apply_column_preferences()
                
                # Apply to reports view if loaded
                if 'reports' in self._views:
                    reports_view = self._views['reports']
                    if hasattr(reports_view, 'apply_column_preferences'):
                        reports_view.apply_column_preferences()
                
                logger.info("Column preferences applied successfully")
        
        except Exception as e:
            logger.error(f"Error showing preferences dialog: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά την εμφάνιση προτιμήσεων:\n\n{str(e)}"
            )
    
    def _check_for_updates(self):
        """Check for application updates."""
        progress = None
        try:
            from services.update_checker import check_for_updates
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl, Qt
            
            # Show progress dialog
            progress = QProgressDialog("Έλεγχος για νέες εκδόσεις...", None, 0, 0, self)
            progress.setWindowTitle("Έλεγχος ενημερώσεων")
            progress.setWindowModality(Qt.WindowModal)
            progress.setCancelButton(None)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.show()
            QApplication.processEvents()
            
            # Check for updates
            has_update, update_info = check_for_updates(
                current_version=config.APP_VERSION,
                update_url=config.UPDATE_CHECKER_CONFIG['update_url'],
                timeout=config.UPDATE_CHECKER_CONFIG['timeout']
            )
            
            # Close progress dialog
            progress.close()
            progress.deleteLater()
            progress = None
            
            if update_info is None:
                # Connection error
                QMessageBox.warning(
                    self,
                    "Σφάλμα Σύνδεσης",
                    "Αποτυχία σύνδεσης με τον server ενημερώσεων.\n\n"
                    "Παρακαλώ ελέγξτε τη σύνδεσή σας στο Internet και δοκιμάστε ξανά αργότερα."
                )
                logger.warning("Update check failed: connection error")
                return
            
            if not has_update:
                # Already up to date
                QMessageBox.information(
                    self,
                    "Ενημερωμένη Έκδοση",
                    f"Έχετε ήδη την πιο πρόσφατη έκδοση ({config.APP_VERSION})."
                )
                logger.info(f"No updates available. Current version: {config.APP_VERSION}")
                return
            
            # New version available - show custom dialog
            from ui.widgets.update_available_dialog import UpdateAvailableDialog
            
            dialog = UpdateAvailableDialog(
                current_version=config.APP_VERSION,
                new_version=update_info.latest_version,
                changelog=update_info.changelog,
                mandatory=update_info.mandatory,
                parent=self
            )
            
            result = dialog.exec()
            
            if result == QDialog.Accepted:
                # Open download URL in browser
                QDesktopServices.openUrl(QUrl(update_info.download_url))
                logger.info(f"Opening download URL: {update_info.download_url}")
                
                # Close application to allow update installation
                logger.info("Closing application for update installation")
                QMessageBox.information(
                    self,
                    "Κλείσιμο Εφαρμογής",
                    "Η εφαρμογή θα κλείσει τώρα για να εγκαταστήσετε την ενημέρωση.\n\n"
                    "Μετά τη λήψη, εκτελέστε το installer για να ενημερώσετε την εφαρμογή."
                )
                QApplication.quit()
            
        except Exception as e:
            # Ensure progress dialog is closed
            if progress:
                progress.close()
            
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά τον έλεγχο ενημερώσεων:\n{str(e)}"
            )
            logger.error(f"Update check error: {e}", exc_info=True)
    
    def _show_about(self):
        """Show about dialog."""
        try:
            from ui.widgets.about_dialog import AboutDialog
            
            dialog = AboutDialog(self)
            dialog.exec()
            
            logger.debug("About dialog closed")
        
        except Exception as e:
            logger.error(f"Error showing about dialog: {e}", exc_info=True)
            # Fallback to simple message box
            about_text = f"""
            <h2>{self.tr_manager.get('app_title')}</h2>
            <p>{self.tr_manager.get('about_description')}</p>
            <p><b>{self.tr_manager.get('about_version')}:</b> {config.APP_VERSION}</p>
            """
            
            QMessageBox.about(
                self,
                self.tr_manager.get('menu_about'),
                about_text
            )
    
    def _restore_preferences(self):
        """
        Restore user preferences from settings.
        Restores window geometry, position, and language preference.
        """
        try:
            # Restore window geometry
            geometry = self.settings.value('window/geometry')
            if geometry:
                self.restoreGeometry(geometry)
                logger.debug("Window geometry restored from preferences")
            
            # Restore window state (maximized, etc.)
            state = self.settings.value('window/state')
            if state:
                self.restoreState(state)
                logger.debug("Window state restored from preferences")
            
            # Restore language preference (if different from default)
            saved_language = self.settings.value('ui/language')
            if saved_language and saved_language != self.tr_manager.get_current_language():
                self.tr_manager.set_language(saved_language)
                logger.info(f"Language preference restored: {saved_language}")
            
            logger.info("User preferences restored successfully")
            
        except Exception as e:
            logger.warning(f"Failed to restore some preferences: {e}")
    
    def _save_preferences(self):
        """
        Save user preferences to settings.
        Saves window geometry, position, and language preference.
        """
        try:
            # Save window geometry
            self.settings.setValue('window/geometry', self.saveGeometry())
            
            # Save window state (maximized, etc.)
            self.settings.setValue('window/state', self.saveState())
            
            # Save language preference
            current_language = self.tr_manager.get_current_language()
            self.settings.setValue('ui/language', current_language)
            
            # Ensure settings are written to disk
            self.settings.sync()
            
            logger.info("User preferences saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
    
    def check_for_updates_on_startup(self):
        """Check for updates on startup if enabled in settings."""
        try:
            # Create a temporary settings view instance just for the update check
            # Don't add it to cache or stacked widget to avoid conflicts
            from ui.widgets.settings_view import SettingsView
            
            # Initialize maintenance service if not already done
            if not self.maintenance_service:
                from services.maintenance_service import MaintenanceService
                self.maintenance_service = MaintenanceService(self.db_connection)
            
            # Create temporary instance (not added to cache)
            temp_settings_view = SettingsView(
                self.settings_service,
                self.tr_manager,
                self.maintenance_service,
                None  # No parent to avoid adding to widget hierarchy
            )
            
            # Call silent update check with main window as parent for dialogs
            temp_settings_view.check_for_updates_silent(parent_window=self)
            logger.info("Startup update check completed")
            
        except Exception as e:
            logger.error(f"Failed to check for updates on startup: {e}")
    
    def closeEvent(self, event):
        """
        Handle window close event with graceful shutdown.
        Saves user preferences and cleans up resources.
        
        Args:
            event: Close event
        """
        logger.info("Application shutdown initiated")
        
        # Save user preferences
        self._save_preferences()
        
        # Close database connection
        try:
            self.db_connection.close()
            logger.info("Database connection closed on application exit")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
        
        # Clean up resources
        try:
            # Clear view cache
            self._views.clear()
            logger.debug("View cache cleared")
        except Exception as e:
            logger.error(f"Error clearing view cache: {e}")
        
        event.accept()
        logger.info("MainWindow closed - graceful shutdown complete")
