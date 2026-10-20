# -*- coding: utf-8 -*-
"""
DB Configurator Window - Simplified UI for database setup only.
"""

import logging
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton,
    QMessageBox, QGroupBox, QFormLayout, QTabWidget,
    QTextEdit, QListWidget, QListWidgetItem, QScrollArea,
    QComboBox
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
import mysql.connector

from configurator.config_service import ConfigService

logger = logging.getLogger(__name__)


class DBConfiguratorWindow(QDialog):
    """Simplified configurator dialog for database setup (embedded in main app)."""
    
    def __init__(self, parent=None):
        """Initialize the DB configurator dialog."""
        super().__init__(parent)
        
        self.config_service = ConfigService()
        
        self._init_ui()
        self._load_db_config()
        
        # Αυτόματο test σύνδεσης κατά το άνοιγμα
        self._auto_test_connection()
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Support CRM - Database Configurator")
        
        # Set app icon
        try:
            from utils.resource_loader import app_icon
            self.setWindowIcon(app_icon())
        except:
            pass  # Icon not critical
        
        self.setMinimumSize(600, 400)
        
        # Main layout (QDialog doesn't need central widget)
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Ρύθμιση Βάσης Δεδομένων")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Tab 1: Connection Settings
        conn_tab = QWidget()
        conn_tab_layout = QVBoxLayout(conn_tab)
        
        # Connection settings group
        conn_group = QGroupBox("Στοιχεία Σύνδεσης MariaDB")
        conn_layout = QFormLayout()
        
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("localhost")
        conn_layout.addRow("Host:", self.host_input)
        
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(3306)
        conn_layout.addRow("Port:", self.port_input)
        
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("root")
        conn_layout.addRow("Username:", self.user_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        conn_layout.addRow("Password:", self.password_input)
        
        self.database_input = QLineEdit()
        self.database_input.setPlaceholderText("supportcrm")
        conn_layout.addRow("Database:", self.database_input)
        
        conn_group.setLayout(conn_layout)
        conn_tab_layout.addWidget(conn_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.test_conn_btn = QPushButton("Δοκιμή Σύνδεσης")
        self.test_conn_btn.clicked.connect(self._test_connection)
        btn_layout.addWidget(self.test_conn_btn)
        
        self.save_conn_btn = QPushButton("Αποθήκευση Ρυθμίσεων")
        self.save_conn_btn.clicked.connect(self._save_db_config)
        btn_layout.addWidget(self.save_conn_btn)
        
        self.init_db_btn = QPushButton("Δημιουργία / Αρχικοποίηση Βάσης")
        self.init_db_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.init_db_btn.clicked.connect(self._initialize_database)
        btn_layout.addWidget(self.init_db_btn)
        
        conn_tab_layout.addLayout(btn_layout)
        
        # Status label
        self.db_status_label = QLabel("Κατάσταση: Μη συνδεδεμένο")
        self.db_status_label.setStyleSheet("color: #F44336; font-weight: bold; margin: 10px;")
        self.db_status_label.setAlignment(Qt.AlignCenter)
        conn_tab_layout.addWidget(self.db_status_label)
        
        # Info label
        info_label = QLabel(
            "Σημείωση: Τα στοιχεία συλλόγου και οι ρυθμίσεις PDF\n"
            "διαχειρίζονται από το κύριο πρόγραμμα (μενού Ρυθμίσεις)."
        )
        info_label.setStyleSheet("color: #757575; font-style: italic; margin: 10px;")
        info_label.setAlignment(Qt.AlignCenter)
        conn_tab_layout.addWidget(info_label)
        
        conn_tab_layout.addStretch()
        
        # Add connection tab
        self.tab_widget.addTab(conn_tab, "Σύνδεση")
        
        # Tab 2: Options (Language & Import)
        options_tab = self._create_options_tab()
        self.tab_widget.addTab(options_tab, "Επιλογές")
        
        # Tab 3: Help
        help_tab = self._create_help_tab()
        self.tab_widget.addTab(help_tab, "Βοήθεια")
        
        layout.addWidget(self.tab_widget)
        layout.addStretch()
    
    def _create_options_tab(self):
        """Create the options tab with language selection and CSV import."""
        options_tab = QWidget()
        options_layout = QVBoxLayout(options_tab)
        
        # Language Selection Group
        lang_group = QGroupBox("🌐 Γλώσσα / Language")
        lang_layout = QVBoxLayout()
        
        lang_info = QLabel("Επιλέξτε τη γλώσσα της εφαρμογής:")
        lang_layout.addWidget(lang_info)
        
        lang_row = QHBoxLayout()
        lang_label = QLabel("Γλώσσα:")
        lang_row.addWidget(lang_label)
        
        self.language_combo = QComboBox()
        self.language_combo.setMinimumWidth(200)
        
        # Get translation manager and add languages
        try:
            from ui.i18n import get_translation_manager
            self.tr_manager = get_translation_manager()
            
            for lang_code, lang_name in self.tr_manager.get_supported_languages().items():
                self.language_combo.addItem(lang_name, lang_code)
            
            # Set current language
            current_lang = self.tr_manager.get_current_language()
            index = self.language_combo.findData(current_lang)
            if index >= 0:
                self.language_combo.setCurrentIndex(index)
            
            self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        except Exception as e:
            logger.warning(f"Could not load translation manager: {e}")
            self.language_combo.addItem("Ελληνικά", "el")
            self.language_combo.addItem("English", "en")
        
        lang_row.addWidget(self.language_combo)
        lang_row.addStretch()
        lang_layout.addLayout(lang_row)
        
        lang_note = QLabel("Σημείωση: Η αλλαγή γλώσσας θα εφαρμοστεί στην επόμενη εκκίνηση.")
        lang_note.setStyleSheet("color: #757575; font-style: italic;")
        lang_layout.addWidget(lang_note)
        
        lang_group.setLayout(lang_layout)
        options_layout.addWidget(lang_group)
        
        # CSV Import Group
        import_group = QGroupBox("📥 Εισαγωγή Δεδομένων")
        import_layout = QVBoxLayout()
        
        import_info = QLabel(
            "Εισαγωγή δεδομένων από αρχεία CSV.\n"
            "Απαιτείται σύνδεση με τη βάση δεδομένων."
        )
        import_info.setWordWrap(True)
        import_layout.addWidget(import_info)
        
        self.import_csv_btn = QPushButton("📂 Εισαγωγή δεδομένων από CSV...")
        self.import_csv_btn.setMinimumHeight(40)
        self.import_csv_btn.setStyleSheet("padding: 10px;")
        self.import_csv_btn.clicked.connect(self._show_import_dialog)
        import_layout.addWidget(self.import_csv_btn)
        
        import_group.setLayout(import_layout)
        options_layout.addWidget(import_group)
        
        options_layout.addStretch()
        
        return options_tab
    
    def _on_language_changed(self, index):
        """Handle language selection change."""
        if index < 0:
            return
        
        lang_code = self.language_combo.itemData(index)
        if lang_code and hasattr(self, 'tr_manager'):
            self.tr_manager.set_language(lang_code)
            logger.info(f"Language changed to: {lang_code}")
            
            QMessageBox.information(
                self,
                "Αλλαγή Γλώσσας",
                "Η γλώσσα άλλαξε επιτυχώς.\n\n"
                "Η αλλαγή θα εφαρμοστεί πλήρως στην επόμενη εκκίνηση της εφαρμογής."
            )
    
    def _create_help_tab(self):
        """Create the help tab with installation instructions."""
        help_tab = QWidget()
        help_layout = QVBoxLayout(help_tab)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # MariaDB Download Section
        mariadb_group = QGroupBox("📥 Λήψη MariaDB")
        mariadb_layout = QVBoxLayout()
        
        mariadb_info = QLabel(
            "Το Support CRM χρειάζεται MariaDB ή MySQL για να λειτουργήσει.\n"
            "Κατεβάστε και εγκαταστήστε την MariaDB από τον επίσημο ιστότοπο:"
        )
        mariadb_info.setWordWrap(True)
        mariadb_layout.addWidget(mariadb_info)
        
        mariadb_btn = QPushButton("🌐 Λήψη MariaDB (mariadb.org)")
        mariadb_btn.setStyleSheet("background-color: #003545; color: white; padding: 10px;")
        mariadb_btn.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://pcp.com.gr/downloads/mariadb-10.11.15.msi")
        ))
        mariadb_layout.addWidget(mariadb_btn)
        
        mariadb_group.setLayout(mariadb_layout)
        scroll_layout.addWidget(mariadb_group)
        
        # Installation Steps
        steps_group = QGroupBox("📋 Βήματα Εγκατάστασης")
        steps_layout = QVBoxLayout()
        
        steps_text = QLabel(
            "<b>1. Εγκατάσταση MariaDB:</b><br>"
            "• Κατεβάστε το MSI installer για Windows<br>"
            "• Κατά την εγκατάσταση, ορίστε κωδικό για τον χρήστη <b>root</b><br>"
            "• Αφήστε το port στο <b>3306</b> (default)<br>"
            "• Επιλέξτε 'Enable UTF8 as default character set'<br><br>"
            
            "<b>2. Ρύθμιση Σύνδεσης:</b><br>"
            "• Στην καρτέλα 'Σύνδεση', συμπληρώστε τα στοιχεία:<br>"
            "  - Host: <b>localhost</b><br>"
            "  - Port: <b>3306</b><br>"
            "  - Username: <b>root</b><br>"
            "  - Password: <b>(ο κωδικός που ορίσατε)</b><br>"
            "  - Database: <b>supportcrm</b><br><br>"
            
            "<b>3. Δημιουργία Βάσης:</b><br>"
            "• Πατήστε 'Δοκιμή Σύνδεσης' για να ελέγξετε τη σύνδεση<br>"
            "• Πατήστε 'Δημιουργία / Αρχικοποίηση Βάσης'<br>"
            "• Η βάση θα δημιουργηθεί αυτόματα με όλους τους πίνακες<br><br>"
            
            "<b>4. Έτοιμο!</b><br>"
            "• Κλείστε το configurator και ξεκινήστε το πρόγραμμα"
        )
        steps_text.setWordWrap(True)
        steps_text.setTextFormat(Qt.RichText)
        steps_layout.addWidget(steps_text)
        
        steps_group.setLayout(steps_layout)
        scroll_layout.addWidget(steps_group)
        
        # Troubleshooting
        trouble_group = QGroupBox("🔧 Αντιμετώπιση Προβλημάτων")
        trouble_layout = QVBoxLayout()
        
        trouble_text = QLabel(
            "<b>Δεν συνδέεται στον server:</b><br>"
            "• Βεβαιωθείτε ότι η υπηρεσία MariaDB τρέχει<br>"
            "• Windows: Services → MariaDB → Start<br><br>"
            
            "<b>Access denied (λάθος κωδικός):</b><br>"
            "• Ελέγξτε το username και password<br>"
            "• Δοκιμάστε με τον χρήστη root<br><br>"
            
            "<b>Η βάση δεν υπάρχει:</b><br>"
            "• Πατήστε 'Δημιουργία / Αρχικοποίηση Βάσης'"
        )
        trouble_text.setWordWrap(True)
        trouble_text.setTextFormat(Qt.RichText)
        trouble_layout.addWidget(trouble_text)
        
        trouble_group.setLayout(trouble_layout)
        scroll_layout.addWidget(trouble_group)
        
        # Additional Links
        links_group = QGroupBox("🔗 Χρήσιμοι Σύνδεσμοι")
        links_layout = QVBoxLayout()
        
        heidi_btn = QPushButton("HeidiSQL - Διαχείριση Βάσης (προαιρετικό)")
        heidi_btn.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://www.heidisql.com/download.php")
        ))
        links_layout.addWidget(heidi_btn)
        
        docs_btn = QPushButton("MariaDB Documentation")
        docs_btn.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://mariadb.com/kb/en/documentation/")
        ))
        links_layout.addWidget(docs_btn)
        
        links_group.setLayout(links_layout)
        scroll_layout.addWidget(links_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        help_layout.addWidget(scroll)
        
        return help_tab
    
    def _load_db_config(self):
        """Load database configuration from file."""
        config = self.config_service.load_config()
        
        self.host_input.setText(config.get('host', 'localhost'))
        self.port_input.setValue(config.get('port', 3306))
        self.user_input.setText(config.get('user', 'root'))
        self.password_input.setText(config.get('password', ''))
        self.database_input.setText(config.get('database', 'supportcrm'))
    
    def _auto_test_connection(self):
        """Αυτόματο test σύνδεσης κατά το άνοιγμα (χωρίς popup)."""
        try:
            config = {
                'host': self.host_input.text() or 'localhost',
                'port': self.port_input.value(),
                'user': self.user_input.text() or 'root',
                'password': self.password_input.text(),
                'database': self.database_input.text() or 'supportcrm'
            }
            
            conn = mysql.connector.connect(
                host=config['host'],
                port=config['port'],
                user=config['user'],
                password=config['password'],
                database=config['database'],
                charset='utf8mb4',
                connection_timeout=5  # Timeout 5 δευτερόλεπτα
            )
            conn.close()
            
            self.db_status_label.setText("Κατάσταση: Συνδεδεμένο ✓")
            self.db_status_label.setStyleSheet("color: #4CAF50; font-weight: bold; margin: 10px;")
            logger.info("Auto connection test successful")
            
        except Exception as e:
            # Πιάνουμε όλα τα exceptions (mysql.connector.Error, RuntimeError, κλπ)
            self.db_status_label.setText("Κατάσταση: Μη συνδεδεμένο ✗")
            self.db_status_label.setStyleSheet("color: #F44336; font-weight: bold; margin: 10px;")
            logger.debug(f"Auto connection test failed: {e}")
    
    def _save_db_config_silent(self):
        """Αποθήκευση ρυθμίσεων χωρίς popup μήνυμα."""
        config = {
            'host': self.host_input.text() or 'localhost',
            'port': self.port_input.value(),
            'user': self.user_input.text() or 'root',
            'password': self.password_input.text(),
            'database': self.database_input.text() or 'supportcrm'
        }
        
        if self.config_service.save_config(config):
            logger.info("Configuration auto-saved after successful connection test")
        else:
            logger.warning("Failed to auto-save configuration")
    
    def _save_db_config(self):
        """Save database configuration to file."""
        config = {
            'host': self.host_input.text() or 'localhost',
            'port': self.port_input.value(),
            'user': self.user_input.text() or 'root',
            'password': self.password_input.text(),
            'database': self.database_input.text() or 'supportcrm'
        }
        
        if self.config_service.save_config(config):
            QMessageBox.information(
                self,
                "Επιτυχία",
                "Οι ρυθμίσεις σύνδεσης αποθηκεύτηκαν επιτυχώς!"
            )
        else:
            QMessageBox.critical(
                self,
                "Σφάλμα",
                "Αποτυχία αποθήκευσης ρυθμίσεων."
            )
    
    def _test_connection(self):
        """Test database connection."""
        try:
            config = {
                'host': self.host_input.text() or 'localhost',
                'port': self.port_input.value(),
                'user': self.user_input.text() or 'root',
                'password': self.password_input.text(),
                'database': self.database_input.text() or 'supportcrm'
            }
            
            # Try to connect
            conn = mysql.connector.connect(
                host=config['host'],
                port=config['port'],
                user=config['user'],
                password=config['password'],
                database=config['database'],
                charset='utf8mb4'
            )
            
            conn.close()
            
            self.db_status_label.setText("Κατάσταση: Συνδεδεμένο ✓")
            self.db_status_label.setStyleSheet("color: #4CAF50; font-weight: bold; margin: 10px;")
            
            # Αυτόματη αποθήκευση μετά από επιτυχή σύνδεση
            self._save_db_config_silent()
            
            QMessageBox.information(
                self,
                "Επιτυχία",
                "Η σύνδεση με τη βάση δεδομένων είναι επιτυχής!\n\n"
                "Οι ρυθμίσεις αποθηκεύτηκαν αυτόματα."
            )
            
            logger.info("Database connection test successful")
            
        except Exception as e:
            self.db_status_label.setText("Κατάσταση: Αποτυχία σύνδεσης ✗")
            self.db_status_label.setStyleSheet("color: #F44336; font-weight: bold; margin: 10px;")
            
            # Parse error and provide helpful message
            error_code = getattr(e, 'errno', None)
            error_msg = str(e)
            
            # Common error codes and user-friendly messages
            if error_code == 1045:  # Access denied
                user_msg = (
                    "❌ Λάθος όνομα χρήστη ή κωδικός!\n\n"
                    f"Το MariaDB/MySQL απέρριψε τη σύνδεση για τον χρήστη '{config['user']}'.\n\n"
                    "Λύσεις:\n"
                    "• Ελέγξτε το username και password\n"
                    "• Βεβαιωθείτε ότι ο χρήστης έχει δικαιώματα πρόσβασης\n"
                    "• Δοκιμάστε με τον root χρήστη"
                )
            elif error_code == 2003:  # Can't connect to server
                user_msg = (
                    "❌ Δεν μπορώ να συνδεθώ στον server!\n\n"
                    f"Το MariaDB/MySQL δεν απαντά στο {config['host']}:{config['port']}\n\n"
                    "Λύσεις:\n"
                    "• Βεβαιωθείτε ότι το MariaDB/MySQL τρέχει\n"
                    "• Ελέγξτε το host και port\n"
                    "• Ελέγξτε το firewall"
                )
            elif error_code == 1049:  # Unknown database
                user_msg = (
                    f"❌ Η βάση δεδομένων '{config['database']}' δεν υπάρχει!\n\n"
                    "Λύσεις:\n"
                    "• Πατήστε 'Δημιουργία / Αρχικοποίηση Βάσης' για να τη δημιουργήσετε\n"
                    "• Ή ελέγξτε το όνομα της βάσης"
                )
            elif error_code == 2005:  # Unknown host
                user_msg = (
                    f"❌ Άγνωστο host '{config['host']}'!\n\n"
                    "Λύσεις:\n"
                    "• Ελέγξτε το hostname/IP address\n"
                    "• Για τοπική βάση χρησιμοποιήστε 'localhost' ή '127.0.0.1'"
                )
            elif error_code == 1044:  # Access denied for database
                user_msg = (
                    f"❌ Δεν έχετε δικαιώματα στη βάση '{config['database']}'!\n\n"
                    f"Ο χρήστης '{config['user']}' δεν έχει πρόσβαση σε αυτή τη βάση.\n\n"
                    "Λύσεις:\n"
                    "• Χρησιμοποιήστε χρήστη με δικαιώματα (π.χ. root)\n"
                    "• Ή δώστε δικαιώματα στον χρήστη με GRANT"
                )
            elif error_code == 2013:  # Lost connection
                user_msg = (
                    "❌ Χάθηκε η σύνδεση με τον server!\n\n"
                    "Λύσεις:\n"
                    "• Ελέγξτε αν το MariaDB/MySQL τρέχει\n"
                    "• Ελέγξτε τη σταθερότητα του δικτύου\n"
                    "• Αυξήστε το timeout στις ρυθμίσεις του server"
                )
            else:
                # Generic error with code
                error_code_str = f" (Error {error_code})" if error_code else ""
                user_msg = (
                    f"❌ Σφάλμα σύνδεσης{error_code_str}:\n\n"
                    f"{error_msg}\n\n"
                    "Συμβουλές:\n"
                    "• Ελέγξτε όλες τις ρυθμίσεις σύνδεσης\n"
                    "• Βεβαιωθείτε ότι το MariaDB/MySQL τρέχει\n"
                    "• Ελέγξτε τα logs του server για περισσότερες πληροφορίες"
                )
            
            QMessageBox.critical(
                self,
                "Σφάλμα Σύνδεσης",
                user_msg
            )
            
            logger.error(f"Database connection test failed (errno {error_code}): {error_msg}")
    
    def _initialize_database(self):
        """Initialize database and schema."""
        reply = QMessageBox.question(
            self,
            "Επιβεβαίωση",
            "Θέλετε να δημιουργήσετε/αρχικοποιήσετε τη βάση δεδομένων;\n\n"
            "Αυτό θα:\n"
            "• Δημιουργήσει τη βάση αν δεν υπάρχει\n"
            "• Δημιουργήσει όλους τους πίνακες (schema.sql)\n"
            "• Δημιουργήσει default εγγραφή app_settings",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            config = {
                'host': self.host_input.text() or 'localhost',
                'port': self.port_input.value(),
                'user': self.user_input.text() or 'root',
                'password': self.password_input.text()
            }
            
            database_name = self.database_input.text() or 'supportcrm'
            
            # Connect without database first
            conn = mysql.connector.connect(
                host=config['host'],
                port=config['port'],
                user=config['user'],
                password=config['password'],
                charset='utf8mb4'
            )
            
            cursor = conn.cursor()
            
            # Create database if not exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                         f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            logger.info(f"Database '{database_name}' created/verified")
            
            cursor.close()
            conn.close()
            
            # Now connect to the database and run schema
            conn = mysql.connector.connect(
                host=config['host'],
                port=config['port'],
                user=config['user'],
                password=config['password'],
                database=database_name,
                charset='utf8mb4'
            )
            
            # Read and execute schema.sql
            # Try consolidated schema first (for frozen builds), then fall back to schema.sql
            if getattr(sys, 'frozen', False):
                # Running as compiled executable - use bundled schema
                base_path = Path(sys._MEIPASS)
                schema_path = base_path / 'db' / 'schema_consolidated.sql'
            else:
                # Running in development
                schema_path = Path(__file__).parent.parent / 'db' / 'schema_consolidated.sql'
            
            if not schema_path.exists():
                raise Exception(f"Schema file not found: {schema_path}")
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Execute schema using multi=True for multiple statements
            cursor = conn.cursor()
            
            # Remove comments and split properly
            statements = []
            current_statement = []
            
            for line in schema_sql.split('\n'):
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('--'):
                    continue
                current_statement.append(line)
                # If line ends with semicolon, it's end of statement
                if line.endswith(';'):
                    stmt = ' '.join(current_statement)
                    if stmt.strip():
                        statements.append(stmt)
                    current_statement = []
            
            # Execute each statement
            for statement in statements:
                try:
                    cursor.execute(statement)
                    logger.debug(f"Executed: {statement[:50]}...")
                except Exception as e:
                    logger.warning(f"Statement failed (may be OK if table exists): {e}")
            
            conn.commit()
            logger.info("Schema executed successfully")
            
            # Check if app_settings has a record, if not create default
            cursor.execute("SELECT COUNT(*) FROM app_settings WHERE id = 1")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Insert default settings
                cursor.execute("""
                    INSERT INTO app_settings (id, org_name, org_short_name, pdf_title)
                    VALUES (1, 'Support CRM', 'Support', 'Βεβαίωση Συνδρομής')
                """)
                conn.commit()
                logger.info("Default app_settings record created")
            
            cursor.close()
            conn.close()
            
            logger.info("Database schema initialized successfully")
            
            QMessageBox.information(
                self,
                "Επιτυχία",
                f"Η βάση δεδομένων '{database_name}' δημιουργήθηκε/αρχικοποιήθηκε επιτυχώς!\n\n"
                "Μπορείτε τώρα να:\n"
                "1. Πατήσετε 'Αποθήκευση Ρυθμίσεων'\n"
                "2. Κλείσετε το configurator\n"
                "3. Εκτελέσετε το κύριο πρόγραμμα (main.py)"
            )
            
            self.db_status_label.setText("Κατάσταση: Αρχικοποιημένο ✓")
            self.db_status_label.setStyleSheet("color: #4CAF50; font-weight: bold; margin: 10px;")
            
        except Exception as e:
            # Handle encoding issues in error message
            try:
                error_msg = str(e)
            except:
                error_msg = repr(e)
            
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Αποτυχία αρχικοποίησης βάσης δεδομένων:\n\n{error_msg}"
            )
            logger.error(f"Database initialization failed: {error_msg}")
    
    def _show_import_dialog(self):
        """Show CSV import dialog."""
        try:
            # First check if database is configured and connected
            config = {
                'host': self.host_input.text() or 'localhost',
                'port': self.port_input.value(),
                'user': self.user_input.text() or 'root',
                'password': self.password_input.text(),
                'database': self.database_input.text() or 'supportcrm'
            }
            
            # Test connection first
            try:
                conn = mysql.connector.connect(
                    host=config['host'],
                    port=config['port'],
                    user=config['user'],
                    password=config['password'],
                    database=config['database'],
                    charset='utf8mb4'
                )
                conn.close()
            except mysql.connector.Error as e:
                QMessageBox.warning(
                    self,
                    "Σφάλμα Σύνδεσης",
                    f"Δεν είναι δυνατή η σύνδεση με τη βάση δεδομένων.\n\n"
                    f"Παρακαλώ ελέγξτε τις ρυθμίσεις σύνδεσης πρώτα.\n\n{str(e)}"
                )
                return
            
            # Import required modules
            from db.connection import DatabaseConnection
            from db.repositories.families_repo import FamiliesRepository
            from db.repositories.members_repo import MembersRepository
            from db.repositories.payments_repo import PaymentsRepository
            from db.repositories.imports_repo import ImportsRepository
            from services.import_service import ImportService
            from ui.i18n import get_translation_manager
            from ui.widgets.import_dialog import ImportDialog
            
            # Create database connection
            db_connection = DatabaseConnection(config)
            
            # Initialize repositories
            families_repo = FamiliesRepository(db_connection)
            members_repo = MembersRepository(db_connection)
            payments_repo = PaymentsRepository(db_connection)
            imports_repo = ImportsRepository(db_connection)
            
            # Initialize import service
            import_service = ImportService(
                families_repo,
                members_repo,
                payments_repo,
                imports_repo
            )
            
            # Get translation manager
            tr_manager = get_translation_manager()
            
            # Show import dialog
            dialog = ImportDialog(
                import_service,
                tr_manager,
                self
            )
            dialog.exec()
            
            # Close database connection
            db_connection.close()
            
            logger.debug("Import dialog closed from configurator")
            
        except Exception as e:
            logger.error(f"Error showing import dialog: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά το άνοιγμα του εργαλείου εισαγωγής:\n\n{str(e)}"
            )
    

