# -*- coding: utf-8 -*-
"""
Settings View - Organization and PDF settings management.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from ui.utils.ui_helpers import gr_question
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QMessageBox, QGroupBox, QFormLayout, QFileDialog,
    QSpinBox, QCheckBox, QColorDialog, QScrollArea, QSizePolicy,
    QApplication, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor

from services.settings_service import SettingsService, AppSettings
from ui.i18n import TranslationManager

logger = logging.getLogger(__name__)


class SettingsView(QWidget):
    """
    Settings view for managing organization info and PDF configuration.
    """
    
    def __init__(self, settings_service: SettingsService, tr_manager: TranslationManager, maintenance_service=None, auth_service=None, parent=None):
        """
        Initialize settings view.
        
        Args:
            settings_service: Settings service instance
            tr_manager: Translation manager
            maintenance_service: Optional maintenance service instance
            auth_service: Optional auth service for user management
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.settings_service = settings_service
        self.tr_manager = tr_manager
        self.maintenance_service = maintenance_service
        self.auth_service = auth_service
        self.current_logo_path = ''
        
        self._init_ui()
        self._load_settings()
    
    def showEvent(self, event):
        """Reload settings when view is shown."""
        super().showEvent(event)
        # Reload settings to get latest counters
        self._load_settings()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Ρυθμίσεις Εφαρμογής")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Create tabs
        self._create_org_tab()
        self._create_pdf_tab()
        self._create_email_tab()
        self._create_numbering_tab()
        self._create_license_tab()
        self._create_backup_tab()
        self._create_maintenance_tab()
        self._create_rustdesk_tab()  # RustDesk remote support settings
    
    def _create_org_tab(self):
        """Create Organization Settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        org_group = QGroupBox("Τίτλος Εκτυπώσεων")
        org_layout = QFormLayout()
        
        self.org_name_input = QLineEdit()
        self.org_name_input.setPlaceholderText("π.χ. Support CRM - Τεχνική Υποστήριξη")
        org_layout.addRow("Επωνυμία:", self.org_name_input)
        
        self.org_short_name_input = QLineEdit()
        self.org_short_name_input.setPlaceholderText("π.χ. Support CRM")
        org_layout.addRow("Συντομογραφία:", self.org_short_name_input)
        
        self.org_address_input = QLineEdit()
        self.org_address_input.setPlaceholderText("π.χ. Οδός Τεχνολογίας 10")
        org_layout.addRow("Διεύθυνση:", self.org_address_input)
        
        self.org_city_input = QLineEdit()
        self.org_city_input.setPlaceholderText("π.χ. Αθήνα")
        org_layout.addRow("Πόλη:", self.org_city_input)
        
        self.org_postal_input = QLineEdit()
        self.org_postal_input.setPlaceholderText("π.χ. 10000")
        org_layout.addRow("Τ.Κ.:", self.org_postal_input)
        
        self.org_phone_input = QLineEdit()
        self.org_phone_input.setPlaceholderText("π.χ. 2101234567")
        org_layout.addRow("Τηλέφωνο:", self.org_phone_input)
        
        self.org_email_input = QLineEdit()
        self.org_email_input.setPlaceholderText("π.χ. support@example.com")
        org_layout.addRow("Email:", self.org_email_input)
        
        self.org_afm_input = QLineEdit()
        self.org_afm_input.setPlaceholderText("π.χ. 123456789")
        org_layout.addRow("ΑΦΜ:", self.org_afm_input)
        
        org_group.setLayout(org_layout)
        layout.addWidget(org_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.save_org_btn = QPushButton("Αποθήκευση")
        self.save_org_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_org_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_org_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, "Τίτλος Εκτυπώσεων")
    
    def _create_pdf_tab(self):
        """Create PDF Settings tab for Support CRM."""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # ========== Invoice PDF Settings ==========
        invoice_pdf_group = QGroupBox("PDF Τιμολογίου")
        invoice_pdf_layout = QFormLayout()
        invoice_pdf_layout.setContentsMargins(16, 16, 16, 16)
        invoice_pdf_layout.setVerticalSpacing(10)
        
        self.pdf_invoice_title_input = QLineEdit()
        self.pdf_invoice_title_input.setPlaceholderText("π.χ. Τιμολόγιο Υπηρεσιών")
        invoice_pdf_layout.addRow("Τίτλος:", self.pdf_invoice_title_input)
        
        self.pdf_invoice_footer_input = QLineEdit()
        self.pdf_invoice_footer_input.setPlaceholderText("Προαιρετική σημείωση στο κάτω μέρος")
        invoice_pdf_layout.addRow("Σημείωση:", self.pdf_invoice_footer_input)
        
        invoice_pdf_group.setLayout(invoice_pdf_layout)
        layout.addWidget(invoice_pdf_group)
        
        # ========== Payment Receipt PDF Settings ==========
        payment_pdf_group = QGroupBox("PDF Απόδειξης Πληρωμής")
        payment_pdf_layout = QFormLayout()
        payment_pdf_layout.setContentsMargins(16, 16, 16, 16)
        payment_pdf_layout.setVerticalSpacing(10)
        
        self.pdf_payment_title_input = QLineEdit()
        self.pdf_payment_title_input.setPlaceholderText("π.χ. Απόδειξη Πληρωμής")
        payment_pdf_layout.addRow("Τίτλος:", self.pdf_payment_title_input)
        
        self.pdf_payment_footer_input = QLineEdit()
        self.pdf_payment_footer_input.setPlaceholderText("Προαιρετική σημείωση στο κάτω μέρος")
        payment_pdf_layout.addRow("Σημείωση:", self.pdf_payment_footer_input)
        
        payment_pdf_group.setLayout(payment_pdf_layout)
        layout.addWidget(payment_pdf_group)
        
        # ========== Appearance (receipt / invoice) ==========
        appearance_group = QGroupBox("Εμφάνιση Απόδειξης / Τιμολογίου")
        appearance_layout = QFormLayout()
        appearance_layout.setContentsMargins(16, 16, 16, 16)
        appearance_layout.setVerticalSpacing(10)

        color_row = QHBoxLayout()
        self.pdf_accent_color_input = QLineEdit()
        self.pdf_accent_color_input.setPlaceholderText("#1565C0")
        self.pdf_accent_color_input.setMaximumWidth(120)
        self.pick_accent_btn = QPushButton("Επιλογή χρώματος…")
        self.pick_accent_btn.clicked.connect(self._pick_accent_color)
        color_row.addWidget(self.pdf_accent_color_input)
        color_row.addWidget(self.pick_accent_btn)
        color_row.addStretch()
        _color_wrap = QWidget()
        _color_wrap.setLayout(color_row)
        appearance_layout.addRow("Χρώμα (accent):", _color_wrap)

        self.pdf_show_qr_checkbox = QCheckBox("Εμφάνιση QR (ηλεκτρονική σήμανση)")
        appearance_layout.addRow("", self.pdf_show_qr_checkbox)
        self.pdf_show_session_checkbox = QCheckBox("Εμφάνιση στοιχείων συνεδρίας")
        appearance_layout.addRow("", self.pdf_show_session_checkbox)

        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)

        # ========== Logo section ==========
        logo_group = QGroupBox("Logo Εταιρείας")
        logo_layout = QVBoxLayout()
        logo_layout.setContentsMargins(16, 16, 16, 16)
        
        logo_btn_layout = QHBoxLayout()
        self.select_logo_btn = QPushButton("Επιλογή Logo")
        self.select_logo_btn.clicked.connect(self._select_logo)
        logo_btn_layout.addWidget(self.select_logo_btn)
        
        self.logo_path_label = QLabel("Δεν έχει επιλεγεί logo")
        self.logo_path_label.setStyleSheet("color: #757575;")
        logo_btn_layout.addWidget(self.logo_path_label)
        logo_btn_layout.addStretch()
        
        logo_layout.addLayout(logo_btn_layout)
        
        # Logo preview
        self.logo_preview = QLabel()
        self.logo_preview.setAlignment(Qt.AlignCenter)
        self.logo_preview.setMinimumHeight(120)
        self.logo_preview.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        self.logo_preview.setText("Προεπισκόπηση Logo")
        logo_layout.addWidget(self.logo_preview)
        
        logo_group.setLayout(logo_layout)
        layout.addWidget(logo_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.save_pdf_btn = QPushButton("Αποθήκευση")
        self.save_pdf_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_pdf_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_pdf_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        scroll.setWidget(container)
        tab_layout.addWidget(scroll)
        
        self.tabs.addTab(tab, "Ρυθμίσεις PDF")
    
    def _load_settings(self):
        """Load settings from database and populate form."""
        try:
            settings = self.settings_service.load_settings()
            
            if settings:
                # Organization tab
                self.org_name_input.setText(settings.org_name)
                self.org_short_name_input.setText(settings.org_short_name)
                self.org_address_input.setText(settings.org_address)
                self.org_city_input.setText(settings.org_city)
                self.org_postal_input.setText(settings.org_postal_code)
                self.org_phone_input.setText(settings.org_phone)
                self.org_email_input.setText(settings.org_email)
                self.org_afm_input.setText(settings.org_afm)
                
                # PDF tab - Invoice
                self.pdf_invoice_title_input.setText(settings.pdf_subscription_title or 'ΤΙΜΟΛΟΓΙΟ ΠΑΡΟΧΗΣ ΥΠΗΡΕΣΙΩΝ')
                
                # PDF tab - Payment Receipt
                self.pdf_payment_title_input.setText(settings.pdf_payment_title or 'ΑΠΟΔΕΙΞΗ ΠΑΡΟΧΗΣ ΥΠΗΡΕΣΙΩΝ')
                
                # PDF appearance (receipt / invoice)
                self.pdf_payment_footer_input.setText(settings.pdf_payment_footer or '')
                self.pdf_invoice_footer_input.setText(settings.pdf_subscription_footer or '')
                self.pdf_accent_color_input.setText(getattr(settings, 'pdf_accent_color', '') or '#1565C0')
                self.pdf_show_qr_checkbox.setChecked(bool(getattr(settings, 'pdf_show_qr', True)))
                self.pdf_show_session_checkbox.setChecked(bool(getattr(settings, 'pdf_show_session', True)))
                
                # Logo (fall back to the bundled logo so the preview is never empty)
                _logo_path = settings.pdf_logo_path
                if not _logo_path or not Path(_logo_path).exists():
                    try:
                        from config import BASE_DIR
                        _bundled = Path(BASE_DIR) / 'Logo' / 'main_logo.png'
                        if _bundled.exists():
                            _logo_path = str(_bundled)
                    except Exception:
                        pass
                if _logo_path and Path(_logo_path).exists():
                    self.current_logo_path = _logo_path
                    self._load_logo_preview(_logo_path)
                
                # Email & Notifications tab
                self.smtp_host_input.setText(settings.smtp_host)
                self.smtp_port_input.setText(str(settings.smtp_port))
                self.smtp_use_tls_checkbox.setChecked(settings.smtp_use_tls)
                self.smtp_username_input.setText(settings.smtp_username)
                self.smtp_password_input.setText(settings.smtp_password)
                self.smtp_from_email_input.setText(settings.smtp_from_email)
                self.smtp_from_name_input.setText(settings.smtp_from_name)
                
                self.days_before_expiration_input.setValue(settings.days_before_expiration)
                self.highlight_expirations_checkbox.setChecked(settings.highlight_enabled)
                
                self.expiring_color = settings.color_expiring
                self.expiring_color_preview.setStyleSheet(f"background-color: {settings.color_expiring}; border: 1px solid #ccc;")
                
                self.expired_color = settings.color_expired
                self.expired_color_preview.setStyleSheet(f"background-color: {settings.color_expired}; border: 1px solid #ccc;")
                
                self.email_receipt_subject_input.setText(settings.email_receipt_subject)
                self.email_receipt_body_input.setPlainText(settings.email_receipt_body)
                
                self.email_subscription_subject_input.setText(settings.email_subscription_subject)
                self.email_subscription_body_input.setPlainText(settings.email_subscription_body)
                
                # Email Certificate
                self.email_certificate_subject_input.setText(settings.email_certificate_subject)
                self.email_certificate_body_input.setPlainText(settings.email_certificate_body)
                
                # Numbering tab
                self.receipt_prefix_input.setText(settings.receipt_prefix)
                self.receipt_counter_input.setValue(settings.receipt_counter)
                self.subscription_prefix_input.setText(settings.subscription_prefix)
                self.subscription_counter_input.setValue(settings.subscription_counter)
                self.family_counter_input.setValue(settings.family_counter)
                
                # Update previews
                self._update_receipt_preview()
                self._update_subscription_preview()
                
                # License tab
                self._load_license_info()
                
                # Maintenance tab - auto check updates
                self.auto_check_updates_checkbox.setChecked(settings.auto_check_updates)
                
                # RustDesk tab
                self.rustdesk_host_input.setText(settings.rustdesk_server_host)
                self.rustdesk_port_input.setValue(settings.rustdesk_server_port)
                self.rustdesk_api_key_input.setText(settings.rustdesk_api_key)
                self.rustdesk_relay_input.setText(settings.rustdesk_relay_server)
                self.default_hourly_rate_input.setValue(int(settings.default_hourly_rate))
                
                logger.info("Settings loaded successfully")
            else:
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    "Δεν βρέθηκαν αποθηκευμένες ρυθμίσεις.\n"
                    "Συμπληρώστε τα πεδία και πατήστε Αποθήκευση."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Αποτυχία φόρτωσης ρυθμίσεων:\n{str(e)}"
            )
            logger.error(f"Failed to load settings: {e}")
    
    def _save_settings(self):
        """Save settings from form to database."""
        try:
            # Load current settings to preserve column preferences
            current_settings = self.settings_service.load_settings()
            
            # Create AppSettings from form data
            smtp_host = self.smtp_host_input.text()
            smtp_port_text = self.smtp_port_input.text()
            smtp_username = self.smtp_username_input.text()
            
            logger.info(f"Reading SMTP from form: host={smtp_host}, port={smtp_port_text}, user={smtp_username}")
            
            settings = AppSettings(
                org_name=self.org_name_input.text(),
                org_short_name=self.org_short_name_input.text(),
                org_address=self.org_address_input.text(),
                org_city=self.org_city_input.text(),
                org_postal_code=self.org_postal_input.text(),
                org_phone=self.org_phone_input.text(),
                org_email=self.org_email_input.text(),
                org_afm=self.org_afm_input.text(),
                pdf_logo_path=self.current_logo_path,
                # PDF Settings per document type
                pdf_payment_title=self.pdf_payment_title_input.text() or 'ΑΠΟΔΕΙΞΗ ΠΑΡΟΧΗΣ ΥΠΗΡΕΣΙΩΝ',
                pdf_subscription_title=self.pdf_invoice_title_input.text() or 'ΤΙΜΟΛΟΓΙΟ ΠΑΡΟΧΗΣ ΥΠΗΡΕΣΙΩΝ',
                pdf_payment_footer=self.pdf_payment_footer_input.text(),
                pdf_subscription_footer=self.pdf_invoice_footer_input.text(),
                pdf_accent_color=(self.pdf_accent_color_input.text() or '').strip() or '#1565C0',
                pdf_show_qr=self.pdf_show_qr_checkbox.isChecked(),
                pdf_show_session=self.pdf_show_session_checkbox.isChecked(),
                # SMTP Settings
                smtp_host=smtp_host,
                smtp_port=int(smtp_port_text) if smtp_port_text.isdigit() else 587,
                smtp_use_tls=self.smtp_use_tls_checkbox.isChecked(),
                smtp_username=smtp_username,
                smtp_password=self.smtp_password_input.text(),
                smtp_from_email=self.smtp_from_email_input.text(),
                smtp_from_name=self.smtp_from_name_input.text(),
                # Subscription Notifications
                days_before_expiration=self.days_before_expiration_input.value(),
                highlight_enabled=self.highlight_expirations_checkbox.isChecked(),
                color_expiring=self.expiring_color,
                color_expired=self.expired_color,
                # Email Receipts
                email_receipt_subject=self.email_receipt_subject_input.text() or 'Απόδειξη Πληρωμής',
                email_receipt_body=self.email_receipt_body_input.toPlainText() or 'Σας αποστέλλουμε την απόδειξη πληρωμής σας.',
                # Email Subscription Reminders
                email_subscription_subject=self.email_subscription_subject_input.text() or 'Υπενθύμιση Συνδρομής',
                email_subscription_body=self.email_subscription_body_input.toPlainText() or 'Σας υπενθυμίζουμε ότι η συνδρομή σας λήγει.',
                # Email Family Certificate
                email_certificate_subject=self.email_certificate_subject_input.text() or 'Βεβαίωση Εγγραφής',
                email_certificate_body=self.email_certificate_body_input.toPlainText() or 'Σας αποστέλλουμε τη βεβαίωση εγγραφής σας.',
                # Auto-Numbering Settings
                receipt_counter=self.receipt_counter_input.value(),
                receipt_prefix=self.receipt_prefix_input.text() or 'ΑΠ',
                subscription_counter=self.subscription_counter_input.value(),
                subscription_prefix=self.subscription_prefix_input.text() or 'ΣΥΝ',
                family_counter=self.family_counter_input.value(),
                # Update Checker Settings
                auto_check_updates=self.auto_check_updates_checkbox.isChecked(),
                # RustDesk Settings
                rustdesk_server_host=self.rustdesk_host_input.text(),
                rustdesk_server_port=self.rustdesk_port_input.value(),
                rustdesk_api_key=self.rustdesk_api_key_input.text(),
                rustdesk_relay_server=self.rustdesk_relay_input.text(),
                default_hourly_rate=float(self.default_hourly_rate_input.value())
            )
            
            # Preserve column preferences and license info if they exist
            if current_settings:
                settings.families_visible_columns = current_settings.families_visible_columns
                settings.families_columns_locked = current_settings.families_columns_locked
                settings.payments_visible_columns = current_settings.payments_visible_columns
                settings.payments_columns_locked = current_settings.payments_columns_locked
                settings.subscriptions_visible_columns = current_settings.subscriptions_visible_columns
                settings.subscriptions_columns_locked = current_settings.subscriptions_columns_locked
                settings.reports_visible_columns = current_settings.reports_visible_columns
                settings.reports_columns_locked = current_settings.reports_columns_locked
                # Preserve license information
                settings.license_key = current_settings.license_key
                settings.license_owner = current_settings.license_owner
                settings.license_start_date = current_settings.license_start_date
                settings.license_end_date = current_settings.license_end_date
                settings.license_status = current_settings.license_status
                # Preserve PDF template data (saved from PDF editor)
                settings.pdf_template_family = current_settings.pdf_template_family
                settings.pdf_template_payment = current_settings.pdf_template_payment
                settings.pdf_template_subscription = current_settings.pdf_template_subscription
                # Preserve footer settings (legacy)
                settings.pdf_footer = current_settings.pdf_footer
                # Preserve session/certificate title (legacy, no longer edited in UI)
                settings.pdf_title = current_settings.pdf_title
            
            if self.settings_service.save_settings(settings):
                # Reload settings to ensure cache is updated
                self.settings_service.reload_settings()
                
                QMessageBox.information(
                    self,
                    "Επιτυχία",
                    "Οι ρυθμίσεις αποθηκεύτηκαν επιτυχώς!"
                )
                logger.info("Settings saved successfully")
            else:
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    "Αποτυχία αποθήκευσης ρυθμίσεων."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Αποτυχία αποθήκευσης ρυθμίσεων:\n{str(e)}"
            )
            logger.error(f"Failed to save settings: {e}")
    
    def _select_logo(self):
        """Open file dialog to select logo image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Επιλογή Logo",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_path:
            self.current_logo_path = file_path
            self._load_logo_preview(file_path)
    
    def _load_logo_preview(self, file_path: str):
        """Load and display logo preview."""
        try:
            if not file_path or not Path(file_path).exists():
                self.logo_path_label.setText("Δεν έχει επιλεγεί logo")
                self.logo_path_label.setStyleSheet("color: #757575;")
                self.logo_preview.clear()
                self.logo_preview.setText("Προεπισκόπηση Logo")
                return
            
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # Scale to fit preview area
                scaled_pixmap = pixmap.scaled(
                    200, 150,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.logo_preview.setPixmap(scaled_pixmap)
                self.logo_path_label.setText(file_path)
                self.logo_path_label.setStyleSheet("color: #4CAF50;")
                logger.info(f"Logo loaded: {file_path}")
            else:
                raise Exception("Invalid image file")
        except Exception as e:
            QMessageBox.warning(
                self,
                "Σφάλμα",
                f"Αποτυχία φόρτωσης εικόνας:\n{str(e)}"
            )
            logger.error(f"Failed to load logo: {e}")
    
    def _create_email_tab(self):
        """Create Email & Notifications Settings tab."""
        tab = QWidget()
        # Κύριο layout του tab
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        # Container widget for all content
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)
        
        # ========== SMTP Server Section ==========
        smtp_group = QGroupBox("SMTP Server")
        smtp_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        smtp_layout = QVBoxLayout()
        smtp_layout.setContentsMargins(16, 16, 16, 16)
        smtp_layout.setSpacing(14)  # κάθε γραμμή έχει 14px απόσταση
        
        # Helper function to add SMTP rows
        def add_smtp_row(label_text: str, attr_name: str, is_password: bool = False):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 6, 0, 6)  # Vertical padding για κάθε row
            row_layout.setSpacing(12)  # Horizontal spacing μεταξύ label και field
            
            label = QLabel(label_text)
            label.setMinimumWidth(110)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            edit = QLineEdit()
            edit.setMinimumHeight(32)  # Μεγαλύτερο ύψος
            edit.setStyleSheet("padding: 6px;")  # Padding μέσα στο field
            if is_password:
                edit.setEchoMode(QLineEdit.Password)
            
            setattr(self, attr_name, edit)
            
            row_layout.addWidget(label)
            row_layout.addWidget(edit)
            smtp_layout.addWidget(row)
        
        # Add SMTP fields
        add_smtp_row("SMTP Host:", "smtp_host_input")
        self.smtp_host_input.setPlaceholderText("π.χ. smtp.gmail.com")
        
        add_smtp_row("SMTP Port:", "smtp_port_input")
        self.smtp_port_input.setPlaceholderText("587")
        
        # TLS Checkbox row
        tls_row = QWidget()
        tls_layout = QHBoxLayout(tls_row)
        tls_layout.setContentsMargins(0, 6, 0, 6)  # Vertical padding
        tls_layout.setSpacing(12)  # Horizontal spacing
        tls_label = QLabel("")
        tls_label.setMinimumWidth(110)
        self.smtp_use_tls_checkbox = QCheckBox("Χρήση TLS")
        self.smtp_use_tls_checkbox.setChecked(True)
        self.smtp_use_tls_checkbox.setMinimumHeight(32)  # Ίδιο ύψος με τα fields
        tls_layout.addWidget(tls_label)
        tls_layout.addWidget(self.smtp_use_tls_checkbox)
        tls_layout.addStretch()
        smtp_layout.addWidget(tls_row)
        
        add_smtp_row("Username:", "smtp_username_input")
        self.smtp_username_input.setPlaceholderText("π.χ. user@example.com")
        
        add_smtp_row("Password:", "smtp_password_input", is_password=True)
        self.smtp_password_input.setPlaceholderText("Κωδικός πρόσβασης")
        
        add_smtp_row("From Email:", "smtp_from_email_input")
        self.smtp_from_email_input.setPlaceholderText("π.χ. noreply@example.com")
        
        add_smtp_row("From Name:", "smtp_from_name_input")
        self.smtp_from_name_input.setPlaceholderText("π.χ. Η Επιχείρησή σας")
        
        smtp_layout.addStretch()
        smtp_group.setLayout(smtp_layout)
        
        # Κουμπί "Έλεγχος Σύνδεσης" κάτω από το group με λίγο κενό
        self.test_smtp_btn = QPushButton("Έλεγχος Σύνδεσης")
        self.test_smtp_btn.setMinimumHeight(32)
        self.test_smtp_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.test_smtp_btn.clicked.connect(self._test_smtp_connection)
        
        layout.addWidget(smtp_group)
        layout.addWidget(self.test_smtp_btn)
        
        # ========== Subscription Notifications Section ==========
        subscriptions_group = QGroupBox("Ειδοποιήσεις Συνδρομών")
        subscriptions_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        subscriptions_layout = QFormLayout()
        subscriptions_layout.setContentsMargins(16, 16, 16, 16)
        subscriptions_layout.setVerticalSpacing(10)
        subscriptions_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        self.days_before_expiration_input = QSpinBox()
        self.days_before_expiration_input.setRange(1, 365)
        self.days_before_expiration_input.setValue(30)
        self.days_before_expiration_input.setSuffix(" ημέρες")
        subscriptions_layout.addRow("Ημέρες πριν τη λήξη:", self.days_before_expiration_input)
        
        self.highlight_expirations_checkbox = QCheckBox("Ενεργοποίηση επισήμανσης λήξεων")
        self.highlight_expirations_checkbox.setChecked(True)
        subscriptions_layout.addRow("", self.highlight_expirations_checkbox)
        
        # Color pickers
        color_layout = QHBoxLayout()
        self.expiring_color_btn = QPushButton("Χρώμα λήγουσας")
        self.expiring_color_btn.clicked.connect(lambda: self._pick_color('expiring'))
        self.expiring_color_preview = QLabel()
        self.expiring_color_preview.setFixedSize(30, 30)
        self.expiring_color_preview.setStyleSheet("background-color: #FFA500; border: 1px solid #ccc;")
        self.expiring_color = '#FFA500'
        color_layout.addWidget(self.expiring_color_btn)
        color_layout.addWidget(self.expiring_color_preview)
        color_layout.addStretch()
        subscriptions_layout.addRow("", color_layout)
        
        color_layout2 = QHBoxLayout()
        self.expired_color_btn = QPushButton("Χρώμα ληγμένης")
        self.expired_color_btn.clicked.connect(lambda: self._pick_color('expired'))
        self.expired_color_preview = QLabel()
        self.expired_color_preview.setFixedSize(30, 30)
        self.expired_color_preview.setStyleSheet("background-color: #FF0000; border: 1px solid #ccc;")
        self.expired_color = '#FF0000'
        color_layout2.addWidget(self.expired_color_btn)
        color_layout2.addWidget(self.expired_color_preview)
        color_layout2.addStretch()
        subscriptions_layout.addRow("", color_layout2)
        
        subscriptions_group.setLayout(subscriptions_layout)
        layout.addWidget(subscriptions_group)
        
        # ========== Email Receipt Section ==========
        receipt_group = QGroupBox("Email Απόδειξης Πληρωμής")
        receipt_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        receipt_layout = QFormLayout()
        receipt_layout.setContentsMargins(16, 16, 16, 16)
        receipt_layout.setVerticalSpacing(10)
        receipt_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        self.email_receipt_subject_input = QLineEdit()
        self.email_receipt_subject_input.setPlaceholderText("π.χ. Απόδειξη Πληρωμής")
        receipt_layout.addRow("Θέμα Email:", self.email_receipt_subject_input)
        
        self.email_receipt_body_input = QTextEdit()
        self.email_receipt_body_input.setMaximumHeight(100)
        self.email_receipt_body_input.setPlaceholderText(
            "Placeholders: {client_name}, {payment_date}, {amount}, {receipt_no}, {org_name}"
        )
        receipt_layout.addRow("Κείμενο Email:", self.email_receipt_body_input)
        
        receipt_group.setLayout(receipt_layout)
        layout.addWidget(receipt_group)
        
        # ========== Email Subscription Reminder Section ==========
        subscription_email_group = QGroupBox("Email Υπενθύμισης Συνδρομής")
        subscription_email_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        subscription_email_layout = QFormLayout()
        subscription_email_layout.setContentsMargins(16, 16, 16, 16)
        subscription_email_layout.setVerticalSpacing(10)
        subscription_email_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        self.email_subscription_subject_input = QLineEdit()
        self.email_subscription_subject_input.setPlaceholderText("π.χ. Υπενθύμιση Συνδρομής")
        subscription_email_layout.addRow("Θέμα Email:", self.email_subscription_subject_input)
        
        self.email_subscription_body_input = QTextEdit()
        self.email_subscription_body_input.setMaximumHeight(120)
        self.email_subscription_body_input.setPlaceholderText(
            "Placeholders: {client_name}, {expiry_date}, {total_amount}, {paid_amount}, {remaining_amount}, {org_name}"
        )
        subscription_email_layout.addRow("Κείμενο Email:", self.email_subscription_body_input)
        
        subscription_email_group.setLayout(subscription_email_layout)
        layout.addWidget(subscription_email_group)
        
        # ========== Email Family Certificate Section ==========
        certificate_email_group = QGroupBox("Email Βεβαίωσης Πελάτη")
        certificate_email_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        certificate_email_layout = QFormLayout()
        certificate_email_layout.setContentsMargins(16, 16, 16, 16)
        certificate_email_layout.setVerticalSpacing(10)
        certificate_email_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        self.email_certificate_subject_input = QLineEdit()
        self.email_certificate_subject_input.setPlaceholderText("π.χ. Βεβαίωση Εγγραφής")
        certificate_email_layout.addRow("Θέμα Email:", self.email_certificate_subject_input)
        
        self.email_certificate_body_input = QTextEdit()
        self.email_certificate_body_input.setMaximumHeight(120)
        self.email_certificate_body_input.setPlaceholderText(
            "Placeholders: {client_name}, {org_name}"
        )
        certificate_email_layout.addRow("Κείμενο Email:", self.email_certificate_body_input)
        
        certificate_email_group.setLayout(certificate_email_layout)
        layout.addWidget(certificate_email_group)
        certificate_email_group.setVisible(False)  # hidden: legacy certificate-email tool
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.save_email_btn = QPushButton("Αποθήκευση")
        self.save_email_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_email_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_email_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Add stretch to push content to top
        layout.addStretch(1)
        
        # Set container to scroll area
        scroll.setWidget(container)
        tab_layout.addWidget(scroll)
        
        self.tabs.addTab(tab, "Email - Ειδοποιήσεις")
    
    def _create_numbering_tab(self):
        """Create Auto-Numbering Settings tab with responsive layout."""
        tab = QWidget()
        
        # Root container with main layout
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 10, 20, 10)
        main_layout.setSpacing(16)
        
        # ========== Receipt Numbering Section ==========
        receipts_group = QGroupBox("Αρίθμηση Αποδείξεων (Πεδίο: Αριθμός Απόδειξης)")
        receipts_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        receipts_layout = QFormLayout(receipts_group)
        receipts_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        receipts_layout.setHorizontalSpacing(12)
        receipts_layout.setVerticalSpacing(8)
        receipts_layout.setContentsMargins(12, 10, 12, 10)
        
        # Prefix
        self.receipt_prefix_input = QLineEdit()
        self.receipt_prefix_input.setPlaceholderText("π.χ. ΑΠ")
        self.receipt_prefix_input.setMaxLength(10)
        self.receipt_prefix_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        receipts_layout.addRow("Πρόθεμα:", self.receipt_prefix_input)
        
        # Next number
        self.receipt_counter_input = QSpinBox()
        self.receipt_counter_input.setRange(1, 999999999)
        self.receipt_counter_input.setValue(1)
        self.receipt_counter_input.setButtonSymbols(QSpinBox.NoButtons)
        self.receipt_counter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        receipts_layout.addRow("Επόμενος Αριθμός:", self.receipt_counter_input)
        
        # Connect signals for live preview
        self.receipt_prefix_input.textChanged.connect(self._update_receipt_preview)
        self.receipt_counter_input.valueChanged.connect(self._update_receipt_preview)
        
        main_layout.addWidget(receipts_group)
        
        # ========== Subscription Numbering Section ==========
        subscriptions_group = QGroupBox("Αρίθμηση Συνδρομών (Πεδίο: Κωδικός Συνδρομής)")
        subscriptions_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        subscriptions_layout = QFormLayout(subscriptions_group)
        subscriptions_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        subscriptions_layout.setHorizontalSpacing(12)
        subscriptions_layout.setVerticalSpacing(8)
        subscriptions_layout.setContentsMargins(12, 10, 12, 10)
        
        # Prefix
        self.subscription_prefix_input = QLineEdit()
        self.subscription_prefix_input.setPlaceholderText("π.χ. ΣΥΝ")
        self.subscription_prefix_input.setMaxLength(10)
        self.subscription_prefix_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        subscriptions_layout.addRow("Πρόθεμα:", self.subscription_prefix_input)
        
        # Next number
        self.subscription_counter_input = QSpinBox()
        self.subscription_counter_input.setRange(1, 999999999)
        self.subscription_counter_input.setValue(1)
        self.subscription_counter_input.setButtonSymbols(QSpinBox.NoButtons)
        self.subscription_counter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        subscriptions_layout.addRow("Επόμενος Αριθμός:", self.subscription_counter_input)
        
        # Connect signals for live preview
        self.subscription_prefix_input.textChanged.connect(self._update_subscription_preview)
        self.subscription_counter_input.valueChanged.connect(self._update_subscription_preview)
        
        main_layout.addWidget(subscriptions_group)
        
        # ========== Family Numbering Section ==========
        families_group = QGroupBox("Αρίθμηση Πελατών (Πεδίο: Αριθμός Μητρώου)")
        families_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        families_layout = QFormLayout(families_group)
        families_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        families_layout.setHorizontalSpacing(12)
        families_layout.setVerticalSpacing(8)
        families_layout.setContentsMargins(12, 10, 12, 10)
        
        # Next number (no prefix for families - just a number)
        self.family_counter_input = QSpinBox()
        self.family_counter_input.setRange(1, 999999999)
        self.family_counter_input.setValue(1)
        self.family_counter_input.setButtonSymbols(QSpinBox.NoButtons)
        self.family_counter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        families_layout.addRow("Επόμενος Αριθμός:", self.family_counter_input)
        
        # Info label
        info_label = QLabel(
            "Ο αριθμός μητρώου είναι ένας απλός αριθμός (π.χ. 1, 2, 3, ...) χωρίς πρόθεμα.\n"
            "Αλλάξτε τον αριθμό αν θέλετε ο επόμενος πελάτης να ξεκινήσει από διαφορετικό νούμερο."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        families_layout.addRow("", info_label)
        
        main_layout.addWidget(families_group)
        
        # Add stretch to push content to top
        main_layout.addStretch()
        
        # Buttons at the bottom
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()  # Push buttons to the right
        
        self.save_numbering_btn = QPushButton("Αποθήκευση")
        self.save_numbering_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_numbering_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_numbering_btn)
        
        main_layout.addLayout(btn_layout)
        
        # Set container as tab layout
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(container)
        
        self.tabs.addTab(tab, "Αρίθμηση")
    
    def _update_receipt_preview(self):
        """Update receipt number preview."""
        # Preview functionality removed for cleaner layout
        pass
    
    def _update_subscription_preview(self):
        """Update subscription number preview."""
        # Preview functionality removed for cleaner layout
        pass
    
    def _update_family_preview(self):
        """Update family number preview."""
        # Preview functionality removed for cleaner layout
        pass
    
    def _create_license_tab(self):
        """Create License Management tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Διαχείριση Άδειας Χρήσης")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # ========== License Information Section ==========
        info_group = QGroupBox("Πληροφορίες Άδειας")
        info_layout = QFormLayout()
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setVerticalSpacing(12)
        info_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Owner
        self.license_owner_label = QLabel("-")
        self.license_owner_label.setStyleSheet("font-weight: bold;")
        info_layout.addRow("Ιδιοκτήτης Άδειας:", self.license_owner_label)
        
        # Start date
        self.license_start_label = QLabel("-")
        info_layout.addRow("Ημ/νία Έναρξης:", self.license_start_label)
        
        # End date
        self.license_end_label = QLabel("-")
        info_layout.addRow("Ημ/νία Λήξης:", self.license_end_label)
        
        # Days remaining
        self.license_days_label = QLabel("-")
        self.license_days_label.setStyleSheet("font-weight: bold;")
        info_layout.addRow("Υπολειπόμενες Ημέρες:", self.license_days_label)
        
        # Status
        self.license_status_label = QLabel("-")
        self.license_status_label.setStyleSheet("font-weight: bold; padding: 6px; border-radius: 3px;")
        info_layout.addRow("Κατάσταση:", self.license_status_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # ========== License Activation Section ==========
        activation_group = QGroupBox("Ενεργοποίηση Άδειας")
        activation_layout = QVBoxLayout()
        activation_layout.setContentsMargins(16, 16, 16, 16)
        activation_layout.setSpacing(12)
        
        # Description
        activation_desc = QLabel(
            "Εισάγετε το κλειδί άδειας που σας παρέχεται για να ενεργοποιήσετε την εφαρμογή.\n"
            "Η άδεια ισχύει για 1 έτος από την ημερομηνία ενεργοποίησης."
        )
        activation_desc.setWordWrap(True)
        activation_desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        activation_layout.addWidget(activation_desc)
        
        # License key input
        key_layout = QHBoxLayout()
        key_label = QLabel("Κλειδί Άδειας:")
        key_label.setMinimumWidth(100)
        self.license_key_input = QLineEdit()
        self.license_key_input.setPlaceholderText("π.χ. DEMO-1YEAR")
        self.license_key_input.setMinimumHeight(32)
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.license_key_input)
        activation_layout.addLayout(key_layout)
        
        # Activate button
        self.activate_license_btn = QPushButton("Ενεργοποίηση")
        self.activate_license_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;"
        )
        self.activate_license_btn.clicked.connect(self._activate_license)
        activation_layout.addWidget(self.activate_license_btn)
        
        activation_group.setLayout(activation_layout)
        layout.addWidget(activation_group)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, "Άδεια Χρήσης")
    
    def _activate_license(self):
        """Activate license with provided key."""
        try:
            from services.license_service import LicenseService
            
            license_key = self.license_key_input.text().strip()
            
            if not license_key:
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    "Παρακαλώ εισάγετε κλειδί άδειας."
                )
                return
            
            # Disable button during validation
            self.activate_license_btn.setEnabled(False)
            self.activate_license_btn.setText("Επικύρωση...")
            
            # Try online validation first
            from services.license_validator import check_license_status
            import config
            
            validation_result = check_license_status(
                license_key=license_key,
                validation_url=config.LICENSE_VALIDATION_CONFIG['validation_url'],
                timeout=config.LICENSE_VALIDATION_CONFIG['timeout']
            )
            
            # Validation success flag
            validation_success = False
            owner = None
            start_date = None
            end_date = None
            
            if validation_result['online']:
                # Online validation completed (server responded)
                if validation_result['valid']:
                    # Valid license - use dates from server
                    owner = validation_result['owner_name']
                    start_date = validation_result['start_date']
                    end_date = validation_result['end_date']
                    validation_success = True
                    logger.info(f"Online license validation successful: {owner}")
                else:
                    # Invalid or expired license
                    error_msg = validation_result.get('error', 'Το κλειδί άδειας δεν είναι έγκυρο.')
                    QMessageBox.critical(
                        self,
                        "Μη Έγκυρο Κλειδί",
                        error_msg
                    )
                    logger.warning(f"Invalid license key attempted: {license_key}")
            else:
                # Online validation failed (connection error) - try offline validation
                logger.warning("Online validation failed - trying offline validation")
                
                is_valid, owner, error_msg = LicenseService.validate_and_activate(license_key)
                
                if not is_valid:
                    QMessageBox.warning(
                        self,
                        "Σφάλμα Σύνδεσης",
                        "Αδυναμία επικύρωσης άδειας online.\n\n"
                        "Ελέγξτε τη σύνδεσή σας στο Internet και δοκιμάστε ξανά.\n\n"
                        f"Κλειδί: {license_key}\n\n"
                        "Για δοκιμή offline, χρησιμοποιήστε: DEMO-1YEAR"
                    )
                    logger.warning(f"License validation failed - no connection: {license_key}")
                else:
                    # DEMO key validated offline
                    start_date, end_date = LicenseService.calculate_license_dates()
                    validation_success = True
                    logger.info(f"Offline license validation: {owner}")
            
            # Only proceed if validation succeeded
            if not validation_success:
                return
            
            # Save license to database
            if self.settings_service.set_license(
                license_key=license_key,
                owner=owner,
                start_date=start_date,
                end_date=end_date,
                status='active'
            ):
                # Reload settings to ensure cache is updated
                self.settings_service.reload_settings()
                
                QMessageBox.information(
                    self,
                    "Επιτυχής Ενεργοποίηση",
                    f"Η άδεια ενεργοποιήθηκε επιτυχώς!\n\n"
                    f"Ιδιοκτήτης: {owner}\n"
                    f"Ημ/νία Έναρξης: {start_date.strftime('%d/%m/%Y')}\n"
                    f"Ημ/νία Λήξης: {end_date.strftime('%d/%m/%Y')}\n\n"
                    f"Η άδεια ισχύει για 1 έτος."
                )
                logger.info(f"License activated: {owner}, expires: {end_date}")
                
                # Reload license info display
                self._load_license_info()
                
                # Notify main window to refresh (if it has a refresh method)
                try:
                    main_window = self.window()
                    if hasattr(main_window, 'refresh_license_info'):
                        main_window.refresh_license_info()
                except Exception as e:
                    logger.debug(f"Could not refresh main window license info: {e}")
                
                # Clear input
                self.license_key_input.clear()
            else:
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    "Αποτυχία αποθήκευσης άδειας στη βάση δεδομένων."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα ενεργοποίησης άδειας:\n{str(e)}"
            )
            logger.error(f"License activation error: {e}", exc_info=True)
        finally:
            self.activate_license_btn.setEnabled(True)
            self.activate_license_btn.setText("Ενεργοποίηση")
    
    def _load_license_info(self):
        """Load and display license information."""
        try:
            from services.license_service import LicenseService
            from datetime import datetime
            
            license_info = self.settings_service.get_license_info()
            
            if not license_info or license_info['status'] == 'none':
                self.license_owner_label.setText("-")
                self.license_start_label.setText("-")
                self.license_end_label.setText("-")
                self.license_days_label.setText("-")
                self.license_status_label.setText("Δεν έχει οριστεί άδεια")
                self.license_status_label.setStyleSheet(
                    "font-weight: bold; padding: 6px; border-radius: 3px; "
                    "background-color: #f5f5f5; color: #757575;"
                )
                return
            
            # Display owner
            self.license_owner_label.setText(license_info['owner'] or "-")
            
            # Display dates
            start_date = license_info['start_date']
            end_date = license_info['end_date']
            
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if start_date:
                self.license_start_label.setText(start_date.strftime('%d/%m/%Y'))
            else:
                self.license_start_label.setText("-")
            
            if end_date:
                self.license_end_label.setText(end_date.strftime('%d/%m/%Y'))
                
                # Calculate days remaining
                days_remaining = LicenseService.calculate_days_remaining(end_date)
                
                if days_remaining < 0:
                    self.license_days_label.setText(f"{abs(days_remaining)} (έληξε)")
                    self.license_days_label.setStyleSheet("font-weight: bold; color: #d32f2f;")
                elif days_remaining <= 30:
                    self.license_days_label.setText(str(days_remaining))
                    self.license_days_label.setStyleSheet("font-weight: bold; color: #FF9800;")
                else:
                    self.license_days_label.setText(str(days_remaining))
                    self.license_days_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
                
                # Status
                status_text = LicenseService.get_license_status_text(license_info['status'], days_remaining)
                status_color = LicenseService.get_license_status_color(license_info['status'], days_remaining)
                
                self.license_status_label.setText(status_text)
                self.license_status_label.setStyleSheet(
                    f"font-weight: bold; padding: 6px; border-radius: 3px; "
                    f"background-color: {status_color}; color: white;"
                )
            else:
                self.license_end_label.setText("-")
                self.license_days_label.setText("-")
                self.license_status_label.setText("Άγνωστη κατάσταση")
                self.license_status_label.setStyleSheet(
                    "font-weight: bold; padding: 6px; border-radius: 3px; "
                    "background-color: #f5f5f5; color: #757575;"
                )
                
        except Exception as e:
            logger.error(f"Failed to load license info: {e}", exc_info=True)
    
    def _pick_color(self, color_type: str):
        """Open color picker dialog."""
        current_color = self.expiring_color if color_type == 'expiring' else self.expired_color
        color = QColorDialog.getColor(QColor(current_color), self, "Επιλογή Χρώματος")
        
        if color.isValid():
            color_hex = color.name()
            if color_type == 'expiring':
                self.expiring_color = color_hex
                self.expiring_color_preview.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #ccc;")
            else:
                self.expired_color = color_hex
                self.expired_color_preview.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #ccc;")
    
    def _test_smtp_connection(self):
        """Test SMTP connection with current settings."""
        try:
            host = self.smtp_host_input.text().strip()
            port_text = self.smtp_port_input.text().strip()
            port = int(port_text) if port_text.isdigit() else 587
            use_tls = self.smtp_use_tls_checkbox.isChecked()
            username = self.smtp_username_input.text().strip()
            password = self.smtp_password_input.text()
            
            if not host:
                QMessageBox.warning(self, "Προειδοποίηση", "Παρακαλώ εισάγετε SMTP Host.")
                return
            
            # Disable button during test
            self.test_smtp_btn.setEnabled(False)
            self.test_smtp_btn.setText("Έλεγχος...")
            
            # Try to connect
            if use_tls:
                server = smtplib.SMTP(host, port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(host, port, timeout=10)
            
            # Try to login if credentials provided
            if username and password:
                server.login(username, password)
            
            server.quit()
            
            # Connection successful - save settings automatically
            logger.info(f"SMTP connection test successful: {host}:{port}")
            
            # Save SMTP settings
            try:
                self._save_settings()
                QMessageBox.information(
                    self,
                    "Επιτυχία",
                    "Η σύνδεση με τον SMTP server ήταν επιτυχής!\n\n"
                    "Οι ρυθμίσεις αποθηκεύτηκαν αυτόματα."
                )
            except Exception as save_error:
                QMessageBox.warning(
                    self,
                    "Επιτυχία με Προειδοποίηση",
                    f"Η σύνδεση με τον SMTP server ήταν επιτυχής!\n\n"
                    f"Αλλά η αποθήκευση απέτυχε: {str(save_error)}\n\n"
                    f"Παρακαλώ πατήστε 'Αποθήκευση' χειροκίνητα."
                )
                logger.error(f"Failed to auto-save SMTP settings: {save_error}")
            
        except smtplib.SMTPAuthenticationError:
            QMessageBox.critical(
                self,
                "Σφάλμα Ταυτοποίησης",
                "Αποτυχία ταυτοποίησης. Ελέγξτε το username και password."
            )
            logger.error("SMTP authentication failed")
        except smtplib.SMTPException as e:
            QMessageBox.critical(
                self,
                "Σφάλμα SMTP",
                f"Σφάλμα SMTP:\n{str(e)}"
            )
            logger.error(f"SMTP error: {e}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Σφάλμα Σύνδεσης",
                f"Αποτυχία σύνδεσης με τον SMTP server:\n{str(e)}"
            )
            logger.error(f"SMTP connection test failed: {e}")
        finally:
            # Re-enable button
            self.test_smtp_btn.setEnabled(True)
            self.test_smtp_btn.setText("Έλεγχος Σύνδεσης")
    
    def _create_backup_tab(self):
        """Create Backup tab for database backup and restore."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Αντίγραφα Ασφαλείας Βάσης Δεδομένων")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # ========== Backup Section ==========
        backup_group = QGroupBox("Δημιουργία Αντιγράφου Ασφαλείας")
        backup_layout = QVBoxLayout()
        backup_layout.setSpacing(12)
        
        # Description
        backup_desc = QLabel(
            "Δημιουργήστε αντίγραφο ασφαλείας της βάσης δεδομένων σε ασφαλές μέρος. "
            "Η εφαρμογή κρατά επίσης ΑΥΤΟΜΑΤΟ ημερήσιο backup στον παρακάτω φάκελο."
        )
        backup_desc.setWordWrap(True)
        backup_desc.setStyleSheet("color: #666; margin-bottom: 6px;")
        backup_layout.addWidget(backup_desc)

        # Automatic backups folder + open button
        try:
            from config import BACKUPS_DIR as _BDIR
            _bpath = str(_BDIR)
        except Exception:
            _bpath = ''
        auto_row = QHBoxLayout()
        auto_info = QLabel(f"📁 Φάκελος αυτόματων backup:\n{_bpath}")
        auto_info.setWordWrap(True)
        auto_info.setStyleSheet("color:#2e7d32; font-size:12px;")
        self.open_backups_btn = QPushButton("Άνοιγμα φακέλου")
        self.open_backups_btn.clicked.connect(self._open_backups_folder)
        auto_row.addWidget(auto_info, stretch=1)
        auto_row.addWidget(self.open_backups_btn)
        backup_layout.addLayout(auto_row)
        
        # Destination path
        dest_layout = QHBoxLayout()
        dest_label = QLabel("Προορισμός:")
        dest_label.setMinimumWidth(100)
        self.backup_dest_input = QLineEdit()
        self.backup_dest_input.setReadOnly(True)
        self.backup_dest_input.setPlaceholderText("Επιλέξτε προορισμό για το backup...")
        self.backup_select_btn = QPushButton("Επιλογή...")
        self.backup_select_btn.clicked.connect(self._select_backup_destination)
        dest_layout.addWidget(dest_label)
        dest_layout.addWidget(self.backup_dest_input, stretch=1)
        dest_layout.addWidget(self.backup_select_btn)
        backup_layout.addLayout(dest_layout)
        
        # Create backup button
        self.create_backup_btn = QPushButton("Δημιουργία Backup")
        self.create_backup_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;"
        )
        self.create_backup_btn.setEnabled(False)
        self.create_backup_btn.clicked.connect(self._create_backup)
        backup_layout.addWidget(self.create_backup_btn)
        
        backup_group.setLayout(backup_layout)
        layout.addWidget(backup_group)
        
        # ========== Restore Section ==========
        restore_group = QGroupBox("Επαναφορά από Αντίγραφο Ασφαλείας")
        restore_layout = QVBoxLayout()
        restore_layout.setSpacing(12)
        
        # Warning
        restore_warning = QLabel(
            "⚠️ ΠΡΟΣΟΧΗ: Η επαναφορά θα αντικαταστήσει την τρέχουσα βάση δεδομένων!"
        )
        restore_warning.setWordWrap(True)
        restore_warning.setStyleSheet("color: #d32f2f; font-weight: bold; margin-bottom: 10px;")
        restore_layout.addWidget(restore_warning)
        
        # Source path
        source_layout = QHBoxLayout()
        source_label = QLabel("Αρχείο backup:")
        source_label.setMinimumWidth(100)
        self.restore_source_input = QLineEdit()
        self.restore_source_input.setReadOnly(True)
        self.restore_source_input.setPlaceholderText("Επιλέξτε αρχείο backup...")
        self.restore_select_btn = QPushButton("Επιλογή αρχείου...")
        self.restore_select_btn.clicked.connect(self._select_restore_source)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.restore_source_input, stretch=1)
        source_layout.addWidget(self.restore_select_btn)
        restore_layout.addLayout(source_layout)
        
        # Restore button
        self.restore_backup_btn = QPushButton("Επαναφορά Backup")
        self.restore_backup_btn.setStyleSheet(
            "background-color: #FF9800; color: white; font-weight: bold; padding: 10px;"
        )
        self.restore_backup_btn.setEnabled(False)
        self.restore_backup_btn.clicked.connect(self._restore_backup)
        restore_layout.addWidget(self.restore_backup_btn)
        
        restore_group.setLayout(restore_layout)
        layout.addWidget(restore_group)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, "Backup")
    
    def _open_backups_folder(self):
        """Open the automatic-backups folder in the file explorer."""
        path = ''
        try:
            from config import ensure_backup_dir
            path = str(ensure_backup_dir())
            import os
            os.startfile(path)
        except Exception as e:
            logger.warning(f"Could not open backups folder: {e}")
            QMessageBox.information(self, "Φάκελος Backup",
                                   f"Ο φάκελος των αντιγράφων:\n{path}")

    def _select_backup_destination(self):
        """Open file dialog to select backup destination."""
        from services.backup_service import BackupService
        
        # Get suggested filename
        db_config = self.settings_service.db_connection.config
        backup_service = BackupService(db_config)
        suggested_name = backup_service.get_suggested_backup_name()
        try:
            from config import ensure_backup_dir
            import os as _os
            suggested_name = _os.path.join(str(ensure_backup_dir()), suggested_name)
        except Exception:
            pass
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Επιλογή Προορισμού Backup",
            suggested_name,
            "SQL Files (*.sql);;All Files (*.*)"
        )
        
        if file_path:
            self.backup_dest_input.setText(file_path)
            self.create_backup_btn.setEnabled(True)
    
    def _select_restore_source(self):
        """Open file dialog to select backup file for restore."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Επιλογή Αρχείου Backup",
            "",
            "SQL Files (*.sql);;All Files (*.*)"
        )
        
        if file_path:
            self.restore_source_input.setText(file_path)
            self.restore_backup_btn.setEnabled(True)
    
    def _create_backup(self):
        """Create database backup."""
        try:
            dest_path = self.backup_dest_input.text()
            
            if not dest_path:
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    "Παρακαλώ επιλέξτε προορισμό για το backup."
                )
                return
            
            # Disable button during operation
            self.create_backup_btn.setEnabled(False)
            self.create_backup_btn.setText("Δημιουργία...")
            
            # Get database config
            db_config = self.settings_service.db_connection.config
            
            # Create backup
            from services.backup_service import BackupService
            backup_service = BackupService(db_config)
            
            if backup_service.create_backup(dest_path):
                QMessageBox.information(
                    self,
                    "Επιτυχία",
                    f"Το αντίγραφο ασφαλείας δημιουργήθηκε επιτυχώς!\n\n{dest_path}"
                )
                logger.info(f"Backup created: {dest_path}")
            else:
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    "Αποτυχία δημιουργίας backup. Ελέγξτε τα logs για περισσότερες πληροφορίες."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα δημιουργίας backup:\n{str(e)}"
            )
            logger.error(f"Backup creation failed: {e}", exc_info=True)
        finally:
            self.create_backup_btn.setEnabled(True)
            self.create_backup_btn.setText("Δημιουργία Backup")
    
    def _restore_backup(self):
        """Restore database from backup."""
        try:
            source_path = self.restore_source_input.text()
            
            if not source_path:
                QMessageBox.warning(
                    self,
                    "Προειδοποίηση",
                    "Παρακαλώ επιλέξτε αρχείο backup."
                )
                return
            
            # Confirmation dialog
            reply = gr_question(
                self,
                "Επιβεβαίωση Επαναφοράς",
                "⚠️ ΠΡΟΣΟΧΗ: Η επαναφορά θα αντικαταστήσει την τρέχουσα βάση δεδομένων.\n\n"
                "Θέλετε σίγουρα να συνεχίσετε;",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Disable button during operation
            self.restore_backup_btn.setEnabled(False)
            self.restore_backup_btn.setText("Επαναφορά...")
            
            # Get database config
            db_config = self.settings_service.db_connection.config
            
            # Restore backup
            from services.backup_service import BackupService
            backup_service = BackupService(db_config)
            
            if backup_service.restore_backup(source_path, self.settings_service.db_connection):
                QMessageBox.information(
                    self,
                    "Επιτυχία",
                    "Η επαναφορά ολοκληρώθηκε επιτυχώς!\n\n"
                    "Κάνε επανεκκίνηση του προγράμματος για να ισχύσουν οι αλλαγές."
                )
                logger.info(f"Backup restored from: {source_path}")
            else:
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    "Αποτυχία επαναφοράς backup. Ελέγξτε τα logs για περισσότερες πληροφορίες."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα επαναφοράς backup:\n{str(e)}"
            )
            logger.error(f"Backup restore failed: {e}", exc_info=True)
        finally:
            self.restore_backup_btn.setEnabled(True)
            self.restore_backup_btn.setText("Επαναφορά Backup")
    
    def _create_maintenance_tab(self):
        """Create Maintenance tab."""
        tab = QWidget()
        
        # Main layout for the tab
        outer_layout = QVBoxLayout(tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container widget inside scroll area
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Description
        desc_label = QLabel(
            "Εργαλεία συντήρησης βάσης δεδομένων και ελέγχου ενημερώσεων."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(desc_label)
        
        # ========== Database Repair Section ==========
        db_repair_group = QGroupBox("Επιδιόρθωση Βάσης Δεδομένων")
        db_repair_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        db_repair_layout = QVBoxLayout()
        db_repair_layout.setContentsMargins(16, 16, 16, 16)
        db_repair_layout.setSpacing(12)
        
        db_repair_desc = QLabel(
            "Αναβάθμιση βάσης δεδομένων με εκκρεμείς αλλαγές:\n\n"
            "🔄 Ελέγχει για νέα migrations\n"
            "🔄 Προσθέτει νέες στήλες και πίνακες\n"
            "🔄 Εφαρμόζει τις τελευταίες βελτιώσεις\n\n"
            "Ασφαλής λειτουργία - δεν διαγράφει δεδομένα."
        )
        db_repair_desc.setWordWrap(True)
        db_repair_desc.setStyleSheet("color: #555; margin-bottom: 10px;")
        db_repair_layout.addWidget(db_repair_desc)
        
        self.repair_database_btn = QPushButton("🔧 Επιδιόρθωση & Αναβάθμιση Βάσης")
        self.repair_database_btn.setStyleSheet(
            "background-color: #009688; color: white; font-weight: bold; padding: 12px; font-size: 13px;"
        )
        self.repair_database_btn.setMinimumHeight(50)
        self.repair_database_btn.clicked.connect(self._on_repair_database_clicked)
        db_repair_layout.addWidget(self.repair_database_btn)
        
        db_repair_group.setLayout(db_repair_layout)
        layout.addWidget(db_repair_group)
        
        # ========== Update Checker Section ==========
        update_group = QGroupBox("Έλεγχος ενημερώσεων")
        update_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        update_layout = QVBoxLayout()
        update_layout.setContentsMargins(16, 16, 16, 16)
        update_layout.setSpacing(12)
        
        # Current version display
        import config
        version_layout = QHBoxLayout()
        version_label = QLabel("Τρέχουσα έκδοση:")
        version_label.setMinimumWidth(150)
        self.current_version_label = QLabel(config.APP_VERSION)
        self.current_version_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.current_version_label)
        version_layout.addStretch()
        update_layout.addLayout(version_layout)
        
        # Auto-check on startup checkbox
        self.auto_check_updates_checkbox = QCheckBox("Έλεγχος ενημερώσεων κατά την εκκίνηση")
        self.auto_check_updates_checkbox.setStyleSheet("padding: 5px;")
        self.auto_check_updates_checkbox.stateChanged.connect(self._on_auto_check_updates_changed)
        update_layout.addWidget(self.auto_check_updates_checkbox)
        
        # Check for updates button
        self.check_updates_btn = QPushButton("Έλεγχος για ενημερώσεις")
        self.check_updates_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;"
        )
        self.check_updates_btn.clicked.connect(self._on_check_updates_clicked)
        update_layout.addWidget(self.check_updates_btn)
        
        update_group.setLayout(update_layout)
        layout.addWidget(update_group)
        
        # Payment Status Recalculation
        payment_group = QGroupBox("Κατάσταση Πληρωμών")
        payment_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        payment_layout = QVBoxLayout()
        payment_layout.setContentsMargins(16, 16, 16, 16)
        payment_layout.setSpacing(12)
        
        payment_desc = QLabel(
            "Επαναυπολογίζει την κατάσταση (paid/unpaid/partial) όλων των πληρωμών "
            "με βάση τα ποσά Συνολικό / Πληρωμένο / Υπόλοιπο.\n\n"
            "Χρήσιμο μετά από εισαγωγή δεδομένων ή για διόρθωση ασυνεπειών."
        )
        payment_desc.setWordWrap(True)
        payment_desc.setStyleSheet("color: #555; margin-bottom: 10px;")
        payment_layout.addWidget(payment_desc)
        
        self.recalc_payments_btn = QPushButton("Επαναυπολογισμός Κατάστασης Πληρωμών")
        self.recalc_payments_btn.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; padding: 10px;"
        )
        self.recalc_payments_btn.clicked.connect(self._recalculate_payment_statuses)
        payment_layout.addWidget(self.recalc_payments_btn)
        
        payment_group.setLayout(payment_layout)
        layout.addWidget(payment_group)
        
        # Family Members Count Recalculation
        family_group = QGroupBox("Αριθμός Μελών Πελατών")
        family_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        family_layout = QVBoxLayout()
        family_layout.setContentsMargins(16, 16, 16, 16)
        family_layout.setSpacing(12)
        
        family_desc = QLabel(
            "Επαναυπολογίζει τον αριθμό μελών για κάθε πελάτη "
            "με βάση τα ενεργά μέλη στη βάση δεδομένων.\n\n"
            "Χρήσιμο για συγχρονισμό μετά από προσθήκη/διαγραφή μελών."
        )
        family_desc.setWordWrap(True)
        family_desc.setStyleSheet("color: #555; margin-bottom: 10px;")
        family_layout.addWidget(family_desc)
        
        self.recalc_members_btn = QPushButton("Επαναυπολογισμός Αριθμού Μελών")
        self.recalc_members_btn.setStyleSheet(
            "background-color: #FF9800; color: white; font-weight: bold; padding: 10px;"
        )
        self.recalc_members_btn.clicked.connect(self._recalculate_family_members)
        family_layout.addWidget(self.recalc_members_btn)
        
        family_group.setLayout(family_layout)
        layout.addWidget(family_group)
        family_group.setVisible(False)  # hidden: legacy record-count tool
        
        # ========== Bulk Numbering Assignment Section ==========
        bulk_numbering_group = QGroupBox("Μαζική Αρίθμηση Εγγραφών")
        bulk_numbering_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bulk_numbering_layout = QVBoxLayout()
        bulk_numbering_layout.setContentsMargins(16, 16, 16, 16)
        bulk_numbering_layout.setSpacing(12)
        
        bulk_numbering_desc = QLabel(
            "⚠️ ΠΡΟΣΟΧΗ: Αυτές οι ενέργειες θα ΑΝΤΙΚΑΤΑΣΤΗΣΟΥΝ όλους τους υπάρχοντες αριθμούς!\n\n"
            "Οι εγγραφές θα ταξινομηθούν με βάση την ημερομηνία και θα λάβουν διαδοχικούς αριθμούς.\n\n"
            "• Πελάτες: Ενημερώνει το πεδίο 'Κωδικός'\n"
            "• Πληρωμές: Ενημερώνει το πεδίο 'Αριθμός Απόδειξης'\n"
            "• Συνδρομές: Ενημερώνει το πεδίο 'Κωδικός Συνδρομής'\n\n"
            "Συνιστάται BACKUP πριν από αυτές τις ενέργειες!"
        )
        bulk_numbering_desc.setWordWrap(True)
        bulk_numbering_desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bulk_numbering_desc.setStyleSheet(
            "color: #d32f2f; font-weight: bold; background-color: #FFEBEE; "
            "padding: 10px; border-left: 4px solid #F44336; border-radius: 4px;"
        )
        bulk_numbering_layout.addWidget(bulk_numbering_desc)
        
        # Bulk assign receipt numbers button
        self.bulk_receipts_btn = QPushButton("📝 Μαζική Αρίθμηση Αποδείξεων")
        self.bulk_receipts_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.bulk_receipts_btn.setMinimumHeight(45)
        self.bulk_receipts_btn.setStyleSheet(
            "background-color: #673AB7; color: white; font-weight: bold; padding: 10px;"
        )
        self.bulk_receipts_btn.clicked.connect(self._bulk_assign_receipts)
        bulk_numbering_layout.addWidget(self.bulk_receipts_btn)
        
        # Bulk assign subscription codes button
        self.bulk_subscriptions_btn = QPushButton("📋 Μαζική Αρίθμηση Συνδρομών")
        self.bulk_subscriptions_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.bulk_subscriptions_btn.setMinimumHeight(45)
        self.bulk_subscriptions_btn.setStyleSheet(
            "background-color: #673AB7; color: white; font-weight: bold; padding: 10px;"
        )
        self.bulk_subscriptions_btn.clicked.connect(self._bulk_assign_subscriptions)
        bulk_numbering_layout.addWidget(self.bulk_subscriptions_btn)
        
        # Bulk assign family codes button
        self.bulk_families_btn = QPushButton("👨‍👩‍👧‍👦 Μαζική Αρίθμηση Πελατών")
        self.bulk_families_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.bulk_families_btn.setMinimumHeight(45)
        self.bulk_families_btn.setStyleSheet(
            "background-color: #673AB7; color: white; font-weight: bold; padding: 10px;"
        )
        self.bulk_families_btn.clicked.connect(self._bulk_assign_families)
        bulk_numbering_layout.addWidget(self.bulk_families_btn)
        
        # Bulk assign ALL button
        self.bulk_all_btn = QPushButton("🔄 Μαζική Αρίθμηση ΟΛΩΝ")
        self.bulk_all_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.bulk_all_btn.setMinimumHeight(50)
        self.bulk_all_btn.setStyleSheet(
            "background-color: #D32F2F; color: white; font-weight: bold; padding: 12px; font-size: 13px;"
        )
        self.bulk_all_btn.clicked.connect(self._bulk_assign_all)
        bulk_numbering_layout.addWidget(self.bulk_all_btn)
        
        bulk_numbering_group.setLayout(bulk_numbering_layout)
        layout.addWidget(bulk_numbering_group)
        bulk_numbering_group.setVisible(False)  # hidden: legacy bulk-renumber tool
        
        # ========== Subscriptions Sync Section ==========
        sync_group = QGroupBox("Συγχρονισμός Συνδρομών")
        sync_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sync_layout = QVBoxLayout()
        sync_layout.setContentsMargins(16, 16, 16, 16)
        sync_layout.setSpacing(12)
        
        sync_desc = QLabel(
            "Διαβάζει όλες τις πληρωμές και δημιουργεί/ενημερώνει τις αντίστοιχες συνδρομές:\n\n"
            "• Για κάθε πληρωμή με ημερομηνίες συνδρομής\n"
            "• Δημιουργεί νέα συνδρομή αν δεν υπάρχει\n"
            "• Ενημερώνει υπάρχουσα συνδρομή με τα τελευταία δεδομένα\n"
            "• Υπολογίζει αυτόματα την κατάσταση (active/expired/pending)\n\n"
            "Χρήσιμο μετά από εισαγωγή δεδομένων ή για συγχρονισμό."
        )
        sync_desc.setWordWrap(True)
        sync_desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sync_desc.setStyleSheet("color: #555; margin-bottom: 10px;")
        sync_layout.addWidget(sync_desc)
        
        self.sync_subscriptions_btn = QPushButton("🔄 Συγχρονισμός Συνδρομών από Πληρωμές")
        self.sync_subscriptions_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sync_subscriptions_btn.setMinimumHeight(50)
        self.sync_subscriptions_btn.setStyleSheet(
            "background-color: #1976D2; color: white; font-weight: bold; padding: 12px; font-size: 13px;"
        )
        self.sync_subscriptions_btn.clicked.connect(self._sync_subscriptions)
        sync_layout.addWidget(self.sync_subscriptions_btn)
        
        sync_group.setLayout(sync_layout)
        layout.addWidget(sync_group)
        
        # ========== Duplicate Records Section ==========
        duplicates_group = QGroupBox("Εύρεση Διπλότυπων Εγγραφών")
        duplicates_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        duplicates_layout = QVBoxLayout()
        duplicates_layout.setContentsMargins(16, 16, 16, 16)
        duplicates_layout.setSpacing(12)
        
        duplicates_desc = QLabel(
            "Εντοπίζει διπλότυπες εγγραφές στη βάση δεδομένων:\n\n"
            "• Πελάτες: Ίδιο όνομα + τηλέφωνο/email\n"
            "• Μέλη: Ίδιο όνομα στον ίδιο πελάτη\n"
            "• Πληρωμές: Ίδιος πελάτης + ημερομηνία + ποσό\n"
            "• Συνδρομές: Ίδιος πελάτης + έτος\n\n"
            "Μπορείτε να δείτε και να διαγράψετε τα διπλότυπα."
        )
        duplicates_desc.setWordWrap(True)
        duplicates_desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        duplicates_desc.setStyleSheet("color: #555; margin-bottom: 10px;")
        duplicates_layout.addWidget(duplicates_desc)
        
        self.find_duplicates_btn = QPushButton("🔍 Εύρεση Διπλότυπων Εγγραφών")
        self.find_duplicates_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.find_duplicates_btn.setMinimumHeight(50)
        self.find_duplicates_btn.setStyleSheet(
            "background-color: #E65100; color: white; font-weight: bold; padding: 12px; font-size: 13px;"
        )
        self.find_duplicates_btn.clicked.connect(self._find_duplicate_records)
        duplicates_layout.addWidget(self.find_duplicates_btn)
        
        duplicates_group.setLayout(duplicates_layout)
        layout.addWidget(duplicates_group)
        duplicates_group.setVisible(False)  # hidden: legacy duplicate-finder tool
        
        # Add stretch at the end
        layout.addStretch(1)
        
        # Set container to scroll area
        scroll.setWidget(container)
        
        # Add scroll area to main layout
        outer_layout.addWidget(scroll)
        
        self.tabs.addTab(tab, "Συντήρηση")
    
    def _create_rustdesk_tab(self):
        """Create RustDesk Settings tab for remote support configuration."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Ρυθμίσεις RustDesk - Απομακρυσμένη Υποστήριξη")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Description
        desc_label = QLabel(
            "Ρυθμίστε τη σύνδεση με το RustDesk server για απομακρυσμένη υποστήριξη πελατών.\n"
            "Το RustDesk επιτρέπει την απομακρυσμένη πρόσβαση στους υπολογιστές των πελατών."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(desc_label)
        
        # ========== RustDesk Server Configuration ==========
        server_group = QGroupBox("Ρυθμίσεις RustDesk Server")
        server_layout = QFormLayout()
        server_layout.setContentsMargins(16, 16, 16, 16)
        server_layout.setVerticalSpacing(12)
        server_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Server host
        self.rustdesk_host_input = QLineEdit()
        self.rustdesk_host_input.setPlaceholderText("π.χ. rustdesk.example.com (κενό για public server)")
        self.rustdesk_host_input.setMinimumHeight(32)
        server_layout.addRow("Server Host:", self.rustdesk_host_input)
        
        # Server port
        self.rustdesk_port_input = QSpinBox()
        self.rustdesk_port_input.setRange(1, 65535)
        self.rustdesk_port_input.setValue(21116)
        self.rustdesk_port_input.setMinimumHeight(32)
        server_layout.addRow("Server Port:", self.rustdesk_port_input)
        
        # API Key (optional)
        self.rustdesk_api_key_input = QLineEdit()
        self.rustdesk_api_key_input.setPlaceholderText("API Key (προαιρετικό)")
        self.rustdesk_api_key_input.setEchoMode(QLineEdit.Password)
        self.rustdesk_api_key_input.setMinimumHeight(32)
        server_layout.addRow("API Key:", self.rustdesk_api_key_input)
        
        # Relay server (optional)
        self.rustdesk_relay_input = QLineEdit()
        self.rustdesk_relay_input.setPlaceholderText("π.χ. relay.example.com (προαιρετικό)")
        self.rustdesk_relay_input.setMinimumHeight(32)
        server_layout.addRow("Relay Server:", self.rustdesk_relay_input)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # ========== Billing Configuration ==========
        billing_group = QGroupBox("Ρυθμίσεις Χρέωσης")
        billing_layout = QFormLayout()
        billing_layout.setContentsMargins(16, 16, 16, 16)
        billing_layout.setVerticalSpacing(12)
        billing_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Default hourly rate
        self.default_hourly_rate_input = QSpinBox()
        self.default_hourly_rate_input.setRange(0, 10000)
        self.default_hourly_rate_input.setValue(50)
        self.default_hourly_rate_input.setSuffix(" €/ώρα")
        self.default_hourly_rate_input.setMinimumHeight(32)
        billing_layout.addRow("Προεπιλεγμένη Ωριαία Χρέωση:", self.default_hourly_rate_input)
        
        billing_info = QLabel(
            "Η προεπιλεγμένη ωριαία χρέωση χρησιμοποιείται όταν δεν έχει οριστεί\n"
            "συγκεκριμένη τιμή για τον πελάτη."
        )
        billing_info.setWordWrap(True)
        billing_info.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        billing_layout.addRow("", billing_info)
        
        billing_group.setLayout(billing_layout)
        layout.addWidget(billing_group)
        
        # ========== RustDesk Status ==========
        status_group = QGroupBox("Κατάσταση RustDesk")
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(16, 16, 16, 16)
        status_layout.setSpacing(12)
        
        # Status label
        self.rustdesk_status_label = QLabel("Κατάσταση: Μη ελεγμένο")
        self.rustdesk_status_label.setStyleSheet(
            "font-weight: bold; padding: 10px; border-radius: 5px; "
            "background-color: #f5f5f5; color: #757575;"
        )
        status_layout.addWidget(self.rustdesk_status_label)
        
        # Test connection button
        self.test_rustdesk_btn = QPushButton("🔍 Έλεγχος Διαθεσιμότητας RustDesk")
        self.test_rustdesk_btn.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; padding: 10px;"
        )
        self.test_rustdesk_btn.setMinimumHeight(40)
        self.test_rustdesk_btn.clicked.connect(self._test_rustdesk_connection)
        status_layout.addWidget(self.test_rustdesk_btn)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.save_rustdesk_btn = QPushButton("Αποθήκευση")
        self.save_rustdesk_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_rustdesk_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(self.save_rustdesk_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, "RustDesk")
    
    def _test_rustdesk_connection(self):
        """Test RustDesk availability and configuration."""
        try:
            from services.rustdesk_service import RustDeskService
            
            # Get current settings
            host = self.rustdesk_host_input.text().strip()
            port = self.rustdesk_port_input.value()
            api_key = self.rustdesk_api_key_input.text().strip()
            
            # Create RustDesk service
            rustdesk_service = RustDeskService()
            
            # Configure if custom server specified
            if host:
                rustdesk_service.configure_server(host, port, api_key)
            
            # Test connection
            result = rustdesk_service.test_connection()
            
            if result['available']:
                self.rustdesk_status_label.setText(
                    f"✅ RustDesk Διαθέσιμο\n"
                    f"Εκτελέσιμο: {result['path']}\n"
                    f"Server: {result['server']}"
                )
                self.rustdesk_status_label.setStyleSheet(
                    "font-weight: bold; padding: 10px; border-radius: 5px; "
                    "background-color: #4CAF50; color: white;"
                )
                
                QMessageBox.information(
                    self,
                    "Επιτυχία",
                    f"Το RustDesk είναι διαθέσιμο!\n\n"
                    f"Εκτελέσιμο: {result['path']}\n"
                    f"Server: {result['server']}\n\n"
                    f"Μπορείτε να χρησιμοποιήσετε την απομακρυσμένη υποστήριξη."
                )
            else:
                self.rustdesk_status_label.setText(
                    "❌ RustDesk Μη Διαθέσιμο\n"
                    "Το RustDesk δεν βρέθηκε στο σύστημα"
                )
                self.rustdesk_status_label.setStyleSheet(
                    "font-weight: bold; padding: 10px; border-radius: 5px; "
                    "background-color: #f44336; color: white;"
                )
                
                QMessageBox.warning(
                    self,
                    "RustDesk Μη Διαθέσιμο",
                    "Το RustDesk δεν βρέθηκε στο σύστημα.\n\n"
                    "Παρακαλώ εγκαταστήστε το RustDesk από:\n"
                    "https://rustdesk.com/\n\n"
                    "Μετά την εγκατάσταση, δοκιμάστε ξανά."
                )
                
        except Exception as e:
            self.rustdesk_status_label.setText(
                f"❌ Σφάλμα Ελέγχου\n{str(e)}"
            )
            self.rustdesk_status_label.setStyleSheet(
                "font-weight: bold; padding: 10px; border-radius: 5px; "
                "background-color: #f44336; color: white;"
            )
            
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα ελέγχου RustDesk:\n{str(e)}"
            )
            logger.error(f"RustDesk test failed: {e}", exc_info=True)
    
    def _recalculate_payment_statuses(self):
        """Recalculate payment statuses."""
        if not self.maintenance_service:
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Το maintenance service δεν είναι διαθέσιμο."
            )
            return
        
        # Confirmation dialog
        reply = gr_question(
            self,
            "Επιβεβαίωση",
            "Θέλετε σίγουρα να επαναυπολογιστεί η κατάσταση όλων των πληρωμών;\n\n"
            "Η ενέργεια αυτή θα διορθώσει το status (paid/unpaid/partial) "
            "με βάση τα ποσά Ποσό / Πληρωμένο / Υπόλοιπο.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Disable button during operation
                self.recalc_payments_btn.setEnabled(False)
                self.recalc_payments_btn.setText("Επεξεργασία...")
                
                # Perform recalculation
                updated, total = self.maintenance_service.recalculate_payment_statuses()
                
                # Show result
                if updated == 0:
                    QMessageBox.information(
                        self,
                        "Ολοκληρώθηκε",
                        f"Δεν βρέθηκαν εγγραφές για διόρθωση.\n\n"
                        f"Συνολικές πληρωμές: {total}"
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Ολοκληρώθηκε",
                        f"Ολοκληρώθηκε ο επαναυπολογισμός.\n\n"
                        f"Διορθώθηκαν {updated} από {total} πληρωμές."
                    )
                
                logger.info(f"Payment status recalculation: {updated}/{total} updated")
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    f"Αποτυχία επαναυπολογισμού:\n{str(e)}"
                )
                logger.error(f"Failed to recalculate payment statuses: {e}", exc_info=True)
            
            finally:
                # Re-enable button
                self.recalc_payments_btn.setEnabled(True)
                self.recalc_payments_btn.setText("Επαναυπολογισμός Κατάστασης Πληρωμών")
    
    def _recalculate_family_members(self):
        """Recalculate family members count."""
        if not self.maintenance_service:
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Το maintenance service δεν είναι διαθέσιμο."
            )
            return
        
        # Confirmation dialog
        reply = gr_question(
            self,
            "Επιβεβαίωση",
            "Θέλετε σίγουρα να επαναυπολογιστεί ο αριθμός μελών για όλους τους πελάτες;\n\n"
            "Η ενέργεια αυτή θα ενημερώσει το πεδίο 'Αριθμός Μελών' "
            "με βάση τα ενεργά μέλη κάθε πελάτη.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Disable button during operation
                self.recalc_members_btn.setEnabled(False)
                self.recalc_members_btn.setText("Επεξεργασία...")
                
                # Perform recalculation
                updated, total = self.maintenance_service.recalculate_family_members_count()
                
                # Show result
                if updated == 0:
                    QMessageBox.information(
                        self,
                        "Ολοκληρώθηκε",
                        f"Δεν βρέθηκαν εγγραφές για διόρθωση.\n\n"
                        f"Συνολικοί πελάτες: {total}"
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Ολοκληρώθηκε",
                        f"Ολοκληρώθηκε ο επαναυπολογισμός.\n\n"
                        f"Διορθώθηκαν {updated} από {total} πελάτες."
                    )
                
                logger.info(f"Family members count recalculation: {updated}/{total} updated")
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    f"Αποτυχία επαναυπολογισμού:\n{str(e)}"
                )
                logger.error(f"Failed to recalculate family members: {e}", exc_info=True)
            
            finally:
                # Re-enable button
                self.recalc_members_btn.setEnabled(True)
                self.recalc_members_btn.setText("Επαναυπολογισμός Αριθμού Μελών")
    

    
    def _sync_subscriptions(self):
        """Sync subscriptions from payments."""
        if not self.maintenance_service:
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Το maintenance service δεν είναι διαθέσιμο."
            )
            return
        
        # Confirmation dialog
        reply = gr_question(
            self,
            "Επιβεβαίωση",
            "Θέλετε να συγχρονίσετε τις συνδρομές από τις πληρωμές;\n\n"
            "Η διαδικασία θα:\n"
            "• Διαβάσει όλες τις πληρωμές με ημερομηνίες συνδρομής\n"
            "• Δημιουργήσει νέες συνδρομές όπου δεν υπάρχουν\n"
            "• Ενημερώσει υπάρχουσες συνδρομές με τα τελευταία δεδομένα\n"
            "• Υπολογίσει αυτόματα την κατάσταση κάθε συνδρομής\n\n"
            "Η λειτουργία είναι ασφαλής και δεν διαγράφει δεδομένα.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Disable button during operation
                self.sync_subscriptions_btn.setEnabled(False)
                self.sync_subscriptions_btn.setText("Συγχρονισμός σε εξέλιξη...")
                
                # Create progress dialog
                from PySide6.QtWidgets import QProgressDialog
                progress = QProgressDialog(
                    "Συγχρονισμός συνδρομών...",
                    "Ακύρωση",
                    0,
                    100,
                    self
                )
                progress.setWindowTitle("Συγχρονισμός")
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)
                progress.setValue(0)
                
                def update_progress(current, total, message):
                    if progress.wasCanceled():
                        return
                    progress.setMaximum(total)
                    progress.setValue(current)
                    progress.setLabelText(message)
                    QApplication.processEvents()
                
                # Perform sync
                from PySide6.QtWidgets import QApplication
                results = self.maintenance_service.sync_subscriptions_from_payments(
                    progress_callback=update_progress
                )
                
                progress.close()
                
                # Build result message
                message_parts = []
                
                if results['success']:
                    message_parts.append("✅ Ο συγχρονισμός ολοκληρώθηκε επιτυχώς!\n")
                else:
                    message_parts.append("⚠️ Ο συγχρονισμός ολοκληρώθηκε με σφάλματα.\n")
                
                # Add statistics
                message_parts.append(f"\n📊 Στατιστικά:")
                message_parts.append(f"   • Δημιουργήθηκαν: {results['created']} συνδρομές")
                message_parts.append(f"   • Ενημερώθηκαν: {results['updated']} συνδρομές")
                
                if results['skipped'] > 0:
                    message_parts.append(f"   • Παραλείφθηκαν: {results['skipped']} (λόγω σφαλμάτων)")
                
                # Add messages
                if results['messages']:
                    message_parts.append("\n📋 Λεπτομέρειες:")
                    for msg in results['messages']:
                        message_parts.append(msg)
                
                # Add errors if any
                if results['errors']:
                    message_parts.append("\n\n⚠️ Σφάλματα:")
                    for error in results['errors'][:10]:  # Show first 10 errors
                        message_parts.append(f"   • {error}")
                    if len(results['errors']) > 10:
                        message_parts.append(f"   ... και {len(results['errors']) - 10} ακόμα")
                
                full_message = "\n".join(message_parts)
                
                # Show result dialog
                if results['success']:
                    QMessageBox.information(
                        self,
                        "Επιτυχία",
                        full_message
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Ολοκληρώθηκε με σφάλματα",
                        full_message
                    )
                
                logger.info(
                    f"Subscriptions sync completed: "
                    f"created={results['created']}, updated={results['updated']}, "
                    f"skipped={results['skipped']}, errors={len(results['errors'])}"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Σφάλμα",
                    f"Αποτυχία συγχρονισμού συνδρομών:\n{str(e)}"
                )
                logger.error(f"Failed to sync subscriptions: {e}", exc_info=True)
            
            finally:
                # Re-enable button
                self.sync_subscriptions_btn.setEnabled(True)
                self.sync_subscriptions_btn.setText("🔄 Συγχρονισμός Συνδρομών από Πληρωμές")
    
    def _find_duplicate_records(self):
        """Find and display duplicate records in the database."""
        from PySide6.QtWidgets import QProgressDialog
        
        if not self.maintenance_service:
            QMessageBox.warning(
                self,
                "Προειδοποίηση",
                "Το maintenance service δεν είναι διαθέσιμο."
            )
            return
        
        try:
            # Disable button during operation
            self.find_duplicates_btn.setEnabled(False)
            self.find_duplicates_btn.setText("Αναζήτηση...")
            
            # Create progress dialog
            progress = QProgressDialog(
                "Αναζήτηση διπλότυπων εγγραφών...",
                None,  # No cancel button
                0,
                0,  # Indeterminate progress
                self
            )
            progress.setWindowTitle("Αναζήτηση")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setMinimumWidth(350)
            progress.show()
            QApplication.processEvents()
            
            # Find duplicates
            results = self.maintenance_service.find_duplicate_records()
            
            # Close progress dialog
            progress.close()
            
            # Build result message
            if results['total_duplicates'] == 0:
                QMessageBox.information(
                    self,
                    "Αποτέλεσμα",
                    "✅ Δεν βρέθηκαν διπλότυπες εγγραφές!\n\n"
                    "Η βάση δεδομένων είναι καθαρή."
                )
                return
            
            # Show duplicates dialog
            self._show_duplicates_dialog(results)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Αποτυχία αναζήτησης διπλότυπων:\n{str(e)}"
            )
            logger.error(f"Failed to find duplicates: {e}", exc_info=True)
        
        finally:
            # Re-enable button
            self.find_duplicates_btn.setEnabled(True)
            self.find_duplicates_btn.setText("🔍 Εύρεση Διπλότυπων Εγγραφών")
    
    def _show_duplicates_dialog(self, results: dict):
        """Show dialog with duplicate records and options to fix them."""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
            QTableWidget, QTableWidgetItem, QHeaderView,
            QDialogButtonBox, QLabel
        )
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Διπλότυπες Εγγραφές")
        dialog.setMinimumSize(900, 600)
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # Summary label
        summary = QLabel(
            f"⚠️ Βρέθηκαν {results['total_duplicates']} ομάδες διπλότυπων εγγραφών:\n"
            f"   • Πελάτες: {len(results['families'])}\n"
            f"   • Μέλη: {len(results['members'])}\n"
            f"   • Πληρωμές: {len(results['payments'])}\n"
            f"   • Συνδρομές: {len(results['subscriptions'])}"
        )
        summary.setStyleSheet(
            "background-color: #FFF3E0; padding: 12px; border-radius: 4px; "
            "border-left: 4px solid #FF9800; margin-bottom: 10px;"
        )
        layout.addWidget(summary)
        
        # Tab widget for each table
        tabs = QTabWidget()
        
        # Families tab
        if results['families']:
            families_table = self._create_duplicates_table(
                results['families'],
                ['ID', 'Κωδικός', 'Επώνυμο', 'Όνομα', 'Τηλέφωνο', 'Κινητό', 'Email', 'Διπλότυπα IDs'],
                ['id', 'legacy_code', 'last_name', 'first_name', 'phone', 'mobile', 'email', 'duplicate_ids']
            )
            tabs.addTab(families_table, f"Πελάτες ({len(results['families'])})")
        
        # Members tab
        if results['members']:
            members_table = self._create_duplicates_table(
                results['members'],
                ['ID', 'Πελάτης', 'Όνομα', 'Επώνυμο', 'Ημ. Γέννησης', 'Διπλότυπα IDs'],
                ['id', 'family_name', 'first_name', 'last_name', 'birth_date', 'duplicate_ids']
            )
            tabs.addTab(members_table, f"Μέλη ({len(results['members'])})")
        
        # Payments tab
        if results['payments']:
            payments_table = self._create_duplicates_table(
                results['payments'],
                ['ID', 'Πελάτης', 'Ημερομηνία', 'Ποσό', 'Απόδειξη', 'Περιγραφή', 'Διπλότυπα IDs'],
                ['id', 'family_name', 'payment_date', 'total_amount', 'receipt_no', 'description', 'duplicate_ids']
            )
            tabs.addTab(payments_table, f"Πληρωμές ({len(results['payments'])})")
        
        # Subscriptions tab
        if results['subscriptions']:
            subs_table = self._create_duplicates_table(
                results['subscriptions'],
                ['ID', 'Πελάτης', 'Έτος', 'Κατάσταση', 'Ποσό', 'Διπλότυπα IDs'],
                ['id', 'family_name', 'year', 'status', 'total_amount', 'duplicate_ids']
            )
            tabs.addTab(subs_table, f"Συνδρομές ({len(results['subscriptions'])})")
        
        layout.addWidget(tabs)
        
        # Instructions
        instructions = QLabel(
            "💡 Για να διαγράψετε διπλότυπα, σημειώστε τα IDs που θέλετε να κρατήσετε και "
            "διαγράψτε τα υπόλοιπα χειροκίνητα από τις αντίστοιχες καρτέλες της εφαρμογής."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-style: italic; margin-top: 10px;")
        layout.addWidget(instructions)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec()
    
    def _create_duplicates_table(self, data: list, headers: list, keys: list) -> QTableWidget:
        """Create a table widget for displaying duplicate records."""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(data))
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        for row, record in enumerate(data):
            for col, key in enumerate(keys):
                value = record.get(key, '')
                if value is None:
                    value = ''
                item = QTableWidgetItem(str(value))
                table.setItem(row, col, item)
        
        # Resize columns
        header = table.horizontalHeader()
        for i in range(len(headers) - 1):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(len(headers) - 1, QHeaderView.Stretch)
        
        return table
    
    def _on_check_updates_clicked(self):
        """Handle check for updates button click."""
        try:
            import config
            from services.update_checker import check_for_updates
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            
            # Disable button during check
            self.check_updates_btn.setEnabled(False)
            self.check_updates_btn.setText("Έλεγχος...")
            
            # Check for updates
            has_update, update_info = check_for_updates(
                current_version=config.APP_VERSION,
                update_url=config.UPDATE_CHECKER_CONFIG['update_url'],
                timeout=config.UPDATE_CHECKER_CONFIG['timeout']
            )
            
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
            
            # New version available
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Βρέθηκε νέα έκδοση")
            msg.setText(f"Βρέθηκε νέα έκδοση {update_info.latest_version}.")
            
            # Add changelog if available
            if update_info.changelog:
                msg.setInformativeText(f"Σημειώσεις έκδοσης:\n{update_info.changelog}")
            
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            
            # Customize button text and make them bigger
            yes_button = msg.button(QMessageBox.Yes)
            yes_button.setText("Λήψη ενημέρωσης")
            yes_button.setMinimumWidth(180)
            yes_button.setMinimumHeight(35)
            yes_button.setStyleSheet("font-size: 13px; padding: 8px;")
            
            no_button = msg.button(QMessageBox.No)
            no_button.setText("Άκυρο")
            no_button.setMinimumWidth(120)
            no_button.setMinimumHeight(35)
            no_button.setStyleSheet("font-size: 13px; padding: 8px;")
            
            # Make dialog wider to accommodate buttons
            msg.setStyleSheet("QMessageBox { min-width: 500px; }")
            
            result = msg.exec()
            
            if result == QMessageBox.Yes:
                # Open download URL in browser
                QDesktopServices.openUrl(QUrl(update_info.download_url))
                logger.info(f"Opening download URL: {update_info.download_url}")
                
                # Close the application to allow update installation
                logger.info("Closing application for update installation")
                from PySide6.QtWidgets import QApplication
                QApplication.quit()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Σφάλμα κατά τον έλεγχο ενημερώσεων:\n{str(e)}"
            )
            logger.error(f"Update check error: {e}", exc_info=True)
        finally:
            # Re-enable button
            self.check_updates_btn.setEnabled(True)
            self.check_updates_btn.setText("Έλεγχος για ενημερώσεις")
    
    def _on_auto_check_updates_changed(self, state):
        """Handle auto-check updates checkbox change."""
        try:
            # Load current settings
            settings = self.settings_service.load_settings()
            if settings:
                settings.auto_check_updates = self.auto_check_updates_checkbox.isChecked()
                self.settings_service.save_settings(settings)
                logger.info(f"Auto-check updates set to: {settings.auto_check_updates}")
        except Exception as e:
            logger.error(f"Failed to save auto-check updates setting: {e}")
    
    def check_for_updates_silent(self, parent_window=None):
        """
        Check for updates silently (without showing 'up to date' message).
        Only shows dialog if update is available.
        
        Args:
            parent_window: Parent window for dialogs (defaults to self)
        """
        try:
            import config
            from services.update_checker import check_for_updates
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            
            if parent_window is None:
                parent_window = self
            
            logger.info("Performing silent update check on startup...")
            
            # Check for updates
            has_update, update_info = check_for_updates(
                current_version=config.APP_VERSION,
                update_url=config.UPDATE_CHECKER_CONFIG['update_url'],
                timeout=config.UPDATE_CHECKER_CONFIG['timeout']
            )
            
            if update_info is None:
                # Connection error - fail silently
                logger.warning("Silent update check failed: connection error")
                return
            
            if not has_update:
                # Already up to date - no message
                logger.info(f"No updates available. Current version: {config.APP_VERSION}")
                return
            
            # New version available - show dialog
            msg = QMessageBox(parent_window)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Βρέθηκε νέα έκδοση")
            msg.setText(f"Βρέθηκε νέα έκδοση {update_info.latest_version}.")
            
            # Add changelog if available
            if update_info.changelog:
                # Format changelog if it's a list
                if isinstance(update_info.changelog, list):
                    changelog_text = "\n".join([f"• {item}" for item in update_info.changelog])
                else:
                    changelog_text = update_info.changelog
                msg.setInformativeText(f"Σημειώσεις έκδοσης:\n{changelog_text}")
            
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            
            # Customize button text and make them bigger
            yes_button = msg.button(QMessageBox.Yes)
            yes_button.setText("Λήψη ενημέρωσης")
            yes_button.setMinimumWidth(180)
            yes_button.setMinimumHeight(35)
            yes_button.setStyleSheet("font-size: 13px; padding: 6px;")
            
            no_button = msg.button(QMessageBox.No)
            no_button.setText("Άκυρο")
            no_button.setMinimumWidth(120)
            no_button.setMinimumHeight(35)
            no_button.setStyleSheet("font-size: 13px; padding: 6px;")
            
            # Make dialog wider to accommodate buttons
            msg.setStyleSheet("QMessageBox { min-width: 500px; }")
            
            result = msg.exec()
            
            if result == QMessageBox.Yes:
                # Open download URL in browser
                QDesktopServices.openUrl(QUrl(update_info.download_url))
                logger.info(f"Opening download URL: {update_info.download_url}")
                
                # Close the application to allow update installation
                logger.info("Closing application for update installation")
                from PySide6.QtWidgets import QApplication
                QApplication.quit()
            
        except Exception as e:
            # Fail silently on startup
            logger.error(f"Silent update check error: {e}", exc_info=True)
    
    def _bulk_assign_receipts(self):
        """Bulk assign receipt numbers to all payments."""
        if not self.maintenance_service:
            QMessageBox.warning(self, "Προειδοποίηση", "Το maintenance service δεν είναι διαθέσιμο.")
            return
        
        # Get prefix from settings
        settings = self.settings_service.load_settings()
        prefix = settings.receipt_prefix if settings else 'ΑΠ'
        
        # Confirmation dialog
        reply = gr_question(
            self,
            "⚠️ ΠΡΟΣΟΧΗ - Επιβεβαίωση Μαζικής Αρίθμησης",
            f"Θέλετε σίγουρα να αντικαταστήσετε ΟΛΟΥΣ τους αριθμούς αποδείξεων;\n\n"
            f"Αυτή η ενέργεια θα:\n"
            f"• Ταξινομήσει όλες τις πληρωμές με βάση την ημερομηνία\n"
            f"• Θα δώσει διαδοχικούς αριθμούς ({prefix}-0001, {prefix}-0002, ...)\n"
            f"• Θα ΑΝΤΙΚΑΤΑΣΤΗΣΕΙ όλους τους υπάρχοντες αριθμούς\n\n"
            f"Συνιστάται να έχετε κάνει BACKUP!\n\n"
            f"Θέλετε να συνεχίσετε;",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Create progress dialog
        from PySide6.QtWidgets import QProgressDialog, QApplication
        
        progress = QProgressDialog("Προετοιμασία...", None, 0, 100, self)
        progress.setWindowTitle("Μαζική Αρίθμηση Αποδείξεων")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)  # Remove cancel button
        progress.setValue(0)
        QApplication.processEvents()
        
        try:
            self.bulk_receipts_btn.setEnabled(False)
            self.bulk_receipts_btn.setText("Επεξεργασία...")
            
            # Progress callback
            def update_progress(current, total, message):
                progress.setLabelText(message)
                if total > 0:
                    progress.setValue(int((current / total) * 100))
                QApplication.processEvents()
            
            updated, total = self.maintenance_service.bulk_assign_receipt_numbers(
                prefix,
                progress_callback=update_progress
            )
            
            progress.setValue(100)
            progress.close()
            
            # Auto-refresh views
            self._trigger_views_refresh()
            
            QMessageBox.information(
                self,
                "Ολοκληρώθηκε",
                f"Η μαζική αρίθμηση αποδείξεων ολοκληρώθηκε!\n\n"
                f"Ενημερώθηκαν {updated} από {total} πληρωμές.\n\n"
                f"Οι αριθμοί ξεκινούν από {prefix}-0001"
            )
            logger.info(f"Bulk receipt numbering: {updated}/{total} updated")
            
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία μαζικής αρίθμησης:\n{str(e)}")
            logger.error(f"Bulk receipt numbering failed: {e}", exc_info=True)
        finally:
            self.bulk_receipts_btn.setEnabled(True)
            self.bulk_receipts_btn.setText("📝 Μαζική Αρίθμηση Αποδείξεων")
    
    def _bulk_assign_subscriptions(self):
        """Bulk assign subscription codes to all payments."""
        if not self.maintenance_service:
            QMessageBox.warning(self, "Προειδοποίηση", "Το maintenance service δεν είναι διαθέσιμο.")
            return
        
        # Get prefix from settings
        settings = self.settings_service.load_settings()
        prefix = settings.subscription_prefix if settings else 'ΣΥΝ'
        
        # Confirmation dialog
        reply = gr_question(
            self,
            "⚠️ ΠΡΟΣΟΧΗ - Επιβεβαίωση Μαζικής Αρίθμησης",
            f"Θέλετε σίγουρα να αντικαταστήσετε ΟΛΟΥΣ τους κωδικούς συνδρομών;\n\n"
            f"Αυτή η ενέργεια θα:\n"
            f"• Ταξινομήσει όλες τις συνδρομές με βάση την ημερομηνία\n"
            f"• Θα δώσει διαδοχικούς κωδικούς ({prefix}-0001, {prefix}-0002, ...)\n"
            f"• Θα ΑΝΤΙΚΑΤΑΣΤΗΣΕΙ όλους τους υπάρχοντες κωδικούς\n\n"
            f"Συνιστάται να έχετε κάνει BACKUP!\n\n"
            f"Θέλετε να συνεχίσετε;",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Create progress dialog
        from PySide6.QtWidgets import QProgressDialog, QApplication
        
        progress = QProgressDialog("Προετοιμασία...", None, 0, 100, self)
        progress.setWindowTitle("Μαζική Αρίθμηση Συνδρομών")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)  # Remove cancel button
        progress.setValue(0)
        QApplication.processEvents()
        
        try:
            self.bulk_subscriptions_btn.setEnabled(False)
            self.bulk_subscriptions_btn.setText("Επεξεργασία...")
            
            # Progress callback
            def update_progress(current, total, message):
                progress.setLabelText(message)
                if total > 0:
                    progress.setValue(int((current / total) * 100))
                QApplication.processEvents()
            
            updated, total = self.maintenance_service.bulk_assign_subscription_codes(
                prefix, 
                progress_callback=update_progress
            )
            
            progress.setValue(100)
            progress.close()
            
            # Auto-refresh views
            self._trigger_views_refresh()
            
            QMessageBox.information(
                self,
                "Ολοκληρώθηκε",
                f"Η μαζική αρίθμηση συνδρομών ολοκληρώθηκε!\n\n"
                f"Ενημερώθηκαν {updated} από {total} συνδρομές.\n\n"
                f"Οι κωδικοί ξεκινούν από {prefix}-0001"
            )
            logger.info(f"Bulk subscription numbering: {updated}/{total} updated")
            
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία μαζικής αρίθμησης:\n{str(e)}")
            logger.error(f"Bulk subscription numbering failed: {e}", exc_info=True)
        finally:
            self.bulk_subscriptions_btn.setEnabled(True)
            self.bulk_subscriptions_btn.setText("📋 Μαζική Αρίθμηση Συνδρομών")
    
    def _bulk_assign_families(self):
        """Bulk assign codes to all families."""
        if not self.maintenance_service:
            QMessageBox.warning(self, "Προειδοποίηση", "Το maintenance service δεν είναι διαθέσιμο.")
            return
        
        # Get prefix from settings
        settings = self.settings_service.load_settings()
        prefix = settings.family_prefix if settings else 'ΟΙΚ'
        
        # Confirmation dialog
        reply = gr_question(
            self,
            "⚠️ ΠΡΟΣΟΧΗ - Επιβεβαίωση Μαζικής Αρίθμησης",
            f"Θέλετε σίγουρα να αντικαταστήσετε ΟΛΟΥΣ τους κωδικούς πελατών;\n\n"
            f"Αυτή η ενέργεια θα:\n"
            f"• Ταξινομήσει όλους τους πελάτες με βάση την ημερομηνία δημιουργίας\n"
            f"• Θα δώσει διαδοχικούς κωδικούς (1, 2, 3, ...)\n"
            f"• Θα ΑΝΤΙΚΑΤΑΣΤΗΣΕΙ όλους τους υπάρχοντες κωδικούς\n\n"
            f"Συνιστάται να έχετε κάνει BACKUP!\n\n"
            f"Θέλετε να συνεχίσετε;",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Create progress dialog
        from PySide6.QtWidgets import QProgressDialog, QApplication
        
        progress = QProgressDialog("Προετοιμασία...", None, 0, 100, self)
        progress.setWindowTitle("Μαζική Αρίθμηση Πελατών")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)  # Remove cancel button
        progress.setValue(0)
        QApplication.processEvents()
        
        try:
            self.bulk_families_btn.setEnabled(False)
            self.bulk_families_btn.setText("Επεξεργασία...")
            
            # Progress callback
            def update_progress(current, total, message):
                progress.setLabelText(message)
                if total > 0:
                    progress.setValue(int((current / total) * 100))
                QApplication.processEvents()
            
            updated, total = self.maintenance_service.bulk_assign_family_codes(
                start_number=1,
                progress_callback=update_progress
            )
            
            progress.setValue(100)
            progress.close()
            
            # Auto-refresh views
            self._trigger_views_refresh()
            
            QMessageBox.information(
                self,
                "Ολοκληρώθηκε",
                f"Η μαζική αρίθμηση πελατών ολοκληρώθηκε!\n\n"
                f"Ενημερώθηκαν {updated} από {total} πελάτες.\n\n"
                f"Οι κωδικοί ξεκινούν από 1"
            )
            logger.info(f"Bulk family numbering: {updated}/{total} updated")
            
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία μαζικής αρίθμησης:\n{str(e)}")
            logger.error(f"Bulk family numbering failed: {e}", exc_info=True)
        finally:
            self.bulk_families_btn.setEnabled(True)
            self.bulk_families_btn.setText("👨‍👩‍👧‍👦 Μαζική Αρίθμηση Πελατών")
    
    def _bulk_assign_all(self):
        """Bulk assign all numbers (receipts, subscriptions, families)."""
        if not self.maintenance_service:
            QMessageBox.warning(self, "Προειδοποίηση", "Το maintenance service δεν είναι διαθέσιμο.")
            return
        
        # Confirmation dialog
        reply = gr_question(
            self,
            "⚠️⚠️⚠️ ΠΡΟΣΟΧΗ - Επιβεβαίωση Μαζικής Αρίθμησης ΟΛΩΝ",
            "Θέλετε σίγουρα να αντικαταστήσετε ΟΛΟΥΣ τους αριθμούς σε ΟΛΕΣ τις εγγραφές;\n\n"
            "Αυτή η ενέργεια θα:\n"
            "• Αντικαταστήσει όλους τους αριθμούς αποδείξεων\n"
            "• Αντικαταστήσει όλους τους κωδικούς συνδρομών\n"
            "• Αντικαταστήσει όλους τους κωδικούς πελατών\n\n"
            "⚠️ ΑΥΤΗ ΕΙΝΑΙ ΜΙΑ ΜΟΝΙΜΗ ΑΛΛΑΓΗ!\n"
            "⚠️ ΣΥΝΙΣΤΑΤΑ BACKUP ΠΡΙΝ ΑΠΟ ΑΥΤΗ ΤΗΝ ΕΝΕΡΓΕΙΑ!\n\n"
            "Θέλετε να συνεχίσετε;",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Create progress dialog
        from PySide6.QtWidgets import QProgressDialog, QApplication
        
        progress = QProgressDialog("Προετοιμασία...", None, 0, 100, self)
        progress.setWindowTitle("Μαζική Αρίθμηση")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)  # Remove cancel button
        progress.setValue(0)
        QApplication.processEvents()
        
        try:
            self.bulk_all_btn.setEnabled(False)
            self.bulk_all_btn.setText("Επεξεργασία...")
            
            settings = self.settings_service.load_settings()
            
            # Progress callback
            def update_progress(current, total, message):
                progress.setLabelText(message)
                if total > 0:
                    progress.setValue(int((current / total) * 100))
                QApplication.processEvents()
            
            # Bulk assign receipts
            progress.setLabelText("Αρίθμηση αποδείξεων...")
            r_updated, r_total = self.maintenance_service.bulk_assign_receipt_numbers(
                settings.receipt_prefix if settings else 'ΑΠ',
                progress_callback=update_progress
            )
            
            # Bulk assign subscriptions
            progress.setLabelText("Αρίθμηση συνδρομών...")
            s_updated, s_total = self.maintenance_service.bulk_assign_subscription_codes(
                settings.subscription_prefix if settings else 'ΣΥΝ',
                progress_callback=update_progress
            )
            
            # Bulk assign families
            progress.setLabelText("Αρίθμηση πελατών...")
            f_updated, f_total = self.maintenance_service.bulk_assign_family_codes(
                start_number=1,
                progress_callback=update_progress
            )
            
            progress.setValue(100)
            progress.close()
            
            # Auto-refresh views
            self._trigger_views_refresh()
            
            QMessageBox.information(
                self,
                "Ολοκληρώθηκε",
                f"Η μαζική αρίθμηση ΟΛΩΝ ολοκληρώθηκε!\n\n"
                f"Αποδείξεις: {r_updated}/{r_total}\n"
                f"Συνδρομές: {s_updated}/{s_total}\n"
                f"Πελάτες: {f_updated}/{f_total}\n\n"
                f"Όλες οι εγγραφές έχουν νέους αριθμούς!"
            )
            logger.info(f"Bulk ALL numbering completed")
            
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία μαζικής αρίθμησης:\n{str(e)}")
            logger.error(f"Bulk ALL numbering failed: {e}", exc_info=True)
        finally:
            self.bulk_all_btn.setEnabled(True)
            self.bulk_all_btn.setText("🔄 Μαζική Αρίθμηση ΟΛΩΝ")
    
    def _trigger_views_refresh(self):
        """Trigger refresh of all views in the main window."""
        try:
            # Get the main window (parent)
            main_window = self.parent()
            if main_window and hasattr(main_window, 'view_cache'):
                # Refresh families view if it exists
                if 'families' in main_window.view_cache:
                    families_view = main_window.view_cache['families']
                    if hasattr(families_view, 'refresh'):
                        families_view.refresh()
                        logger.debug("Families view refreshed")
                
                # Refresh payments view if it exists
                if 'payments' in main_window.view_cache:
                    payments_view = main_window.view_cache['payments']
                    if hasattr(payments_view, 'refresh'):
                        payments_view.refresh()
                        logger.debug("Payments view refreshed")
                
                # Refresh subscriptions view if it exists
                if 'subscriptions' in main_window.view_cache:
                    subscriptions_view = main_window.view_cache['subscriptions']
                    if hasattr(subscriptions_view, 'refresh'):
                        subscriptions_view.refresh()
                        logger.debug("Subscriptions view refreshed")
                
                logger.info("All views refreshed after bulk numbering")
        except Exception as e:
            logger.warning(f"Could not refresh views: {e}")
    
    def refresh(self):
        """Refresh the view (reload settings)."""
        self._load_settings()
    
    def update_translations(self):
        """Update UI text with current language translations."""
        # This view uses mostly Greek text, but can be extended for i18n
        pass

    def _on_repair_database_clicked(self):
        """Handle repair database button click."""
        try:
            # Import migration manager
            from db.migration_manager import MigrationManager
            from db.connection import DatabaseConnection
            from config import DATABASE_CONFIG
            
            # Show confirmation dialog with warning
            reply = gr_question(
                self,
                "Επιβεβαίωση",
                "Θέλετε να ελέγξετε και να εφαρμόσετε τυχόν εκκρεμείς αναβαθμίσεις στη βάση δεδομένων?\n\n"
                "⚠️ ΣΗΜΑΝΤΙΚΟ:\n"
                "• Η διαδικασία μπορεί να πάρει μερικά λεπτά\n"
                "• Μην κλείσετε την εφαρμογή κατά τη διάρκεια\n"
                "• Η διαδικασία είναι ασφαλής και δεν θα διαγράψει δεδομένα",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Disable button during operation
            self.repair_database_btn.setEnabled(False)
            self.repair_database_btn.setText("Έλεγχος...")
            
            # CRITICAL: Close main app database connection to release locks
            # This allows migrations to acquire exclusive locks on tables
            main_db_connection = None
            try:
                # Get reference to main window's database connection
                from ui.main_window import MainWindow
                main_window = self.window()
                if hasattr(main_window, 'db_connection'):
                    main_db_connection = main_window.db_connection
                    logger.info("Closing main database connection for migrations...")
                    main_db_connection.close()
            except Exception as e:
                logger.warning(f"Could not close main connection: {e}")
            
            # Create fresh database connection for migrations
            db_connection = DatabaseConnection(DATABASE_CONFIG)
            
            # First, apply pending migrations
            self.repair_database_btn.setText("Εφαρμογή Migrations...")
            from services.maintenance_service import MaintenanceService
            maintenance_service = MaintenanceService(db_connection)
            migration_results = maintenance_service.apply_pending_migrations()
            
            # Then, check and fix missing columns directly
            self.repair_database_btn.setText("Έλεγχος στηλών...")
            missing_columns_fixed = self._check_and_fix_missing_columns(db_connection)
            
            # Create migration manager for final check
            migration_manager = MigrationManager(db_connection)
            
            # Get pending migrations (after applying)
            pending_migrations = migration_manager.get_pending_migrations()
            
            # Check results
            migrations_applied = migration_results['stats'].get('applied', 0)
            migrations_failed = migration_results['stats'].get('failed', 0)
            
            if migrations_failed > 0:
                # Show error dialog
                error_msg = "\n".join(migration_results['errors'])
                QMessageBox.critical(
                    self,
                    "Σφάλμα Migrations",
                    f"Απέτυχαν {migrations_failed} migrations:\n\n{error_msg}\n\n"
                    "Παρακαλώ ελέγξτε τα logs για περισσότερες λεπτομέρειες."
                )
                logger.error(f"Migration failures: {error_msg}")
            elif migrations_applied == 0 and not missing_columns_fixed and not pending_migrations:
                QMessageBox.information(
                    self,
                    "Επιτυχία",
                    "✓ Η βάση δεδομένων είναι ενημερωμένη!\n\n"
                    "Δεν υπάρχουν εκκρεμείς αναβαθμίσεις."
                )
                logger.info("Database is up to date - no pending migrations")
            else:
                # Show success dialog with details
                success_msg = "\n".join(migration_results['messages'])
                if missing_columns_fixed:
                    success_msg += f"\n\n✓ Διορθώθηκαν {missing_columns_fixed} στήλες"
                
                QMessageBox.information(
                    self,
                    "Επιτυχία",
                    f"{success_msg}\n\n"
                    "Η βάση δεδομένων ενημερώθηκε επιτυχώς.\n"
                    "Παρακαλώ επανεκκινήστε την εφαρμογή."
                )
                logger.info(f"Database updated: {migrations_applied} migrations applied")
            
            # Skip the old migration check logic
            if False:  # Disabled - replaced with above logic
                # Show pending migrations
                migration_list = "\n".join([f"• v{m['version']}: {m['description']}" for m in pending_migrations])
                
                reply = gr_question(
                    self,
                    "Εκκρεμείς Αναβαθμίσεις",
                    f"Βρέθηκαν {len(pending_migrations)} εκκρεμείς αναβαθμίσεις:\n\n"
                    f"{migration_list}\n\n"
                    f"Θέλετε να τις εφαρμόσετε τώρα;",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    from PySide6.QtWidgets import QProgressDialog
                    from PySide6.QtCore import Qt
                    from PySide6.QtWidgets import QApplication
                    
                    # Create progress dialog
                    progress = QProgressDialog(
                        "Εφαρμογή migrations...",
                        "Ακύρωση",
                        0,
                        len(pending_migrations),
                        self
                    )
                    progress.setWindowTitle("Αναβάθμιση Βάσης")
                    progress.setWindowModality(Qt.WindowModal)
                    progress.setMinimumDuration(0)
                    progress.setValue(0)
                    progress.setCancelButton(None)  # Disable cancel
                    progress.show()
                    QApplication.processEvents()
                    
                    # Apply migrations
                    success_count = 0
                    failed_count = 0
                    
                    for i, migration in enumerate(pending_migrations):
                        progress.setLabelText(
                            f"Εφαρμογή migration {i+1}/{len(pending_migrations)}:\n"
                            f"v{migration['version']}: {migration['description']}"
                        )
                        progress.setValue(i)
                        QApplication.processEvents()
                        
                        try:
                            if migration_manager.apply_migration(migration):
                                success_count += 1
                                logger.info(f"Applied migration v{migration['version']}: {migration['description']}")
                            else:
                                failed_count += 1
                                logger.error(f"Failed to apply migration v{migration['version']}: {migration['description']}")
                        except Exception as e:
                            failed_count += 1
                            logger.error(f"Error applying migration v{migration['version']}: {e}")
                    
                    # Close progress dialog
                    progress.setValue(len(pending_migrations))
                    progress.close()
                    
                    # Show results
                    if failed_count == 0:
                        QMessageBox.information(
                            self,
                            "Επιτυχία",
                            f"✓ Εφαρμόστηκαν επιτυχώς {success_count} αναβαθμίσεις!\n\n"
                            f"Η βάση δεδομένων είναι πλέον ενημερωμένη."
                        )
                        logger.info(f"Successfully applied {success_count} migrations")
                    else:
                        QMessageBox.warning(
                            self,
                            "Μερική Επιτυχία",
                            f"Εφαρμόστηκαν {success_count} αναβαθμίσεις.\n"
                            f"Απέτυχαν {failed_count} αναβαθμίσεις.\n\n"
                            f"Ελέγξτε το log για λεπτομέρειες."
                        )
            
            # Close migration database connection
            db_connection.close()
            
            # Reconnect main application database connection
            if main_db_connection:
                try:
                    logger.info("Reconnecting main database connection...")
                    main_db_connection.get_connection()  # This will reconnect automatically
                    logger.info("Main database connection restored")
                except Exception as e:
                    logger.error(f"Failed to reconnect main database: {e}")
                    QMessageBox.warning(
                        self,
                        "Προειδοποίηση",
                        "Τα migrations ολοκληρώθηκαν αλλά η σύνδεση με τη βάση χρειάζεται επανεκκίνηση.\n\n"
                        "Παρακαλώ επανεκκινήστε την εφαρμογή."
                    )
            
        except Exception as e:
            logger.error(f"Error in database repair: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Αποτυχία επιδιόρθωσης βάσης δεδομένων:\n\n{str(e)}"
            )
        
        finally:
            # Re-enable button
            self.repair_database_btn.setEnabled(True)
            self.repair_database_btn.setText("🔧 Επιδιόρθωση & Αναβάθμιση Βάσης")
    
    def _check_and_fix_missing_columns(self, db_connection) -> int:
        """
        Check for missing columns and add them if needed.
        
        Returns:
            Number of columns fixed
        """
        fixed_count = 0
        
        try:
            connection = db_connection.get_connection()
            
            # Define expected columns for families table
            families_columns = {
                'father_name': "ALTER TABLE families ADD COLUMN father_name VARCHAR(100) COMMENT 'Father name' AFTER first_name",
                'spouse_name': "ALTER TABLE families ADD COLUMN spouse_name VARCHAR(100) COMMENT 'Spouse name' AFTER father_name",
                'spouse_maiden_name': "ALTER TABLE families ADD COLUMN spouse_maiden_name VARCHAR(100) COMMENT 'Spouse maiden name' AFTER spouse_name",
                'is_divorced': "ALTER TABLE families ADD COLUMN is_divorced TINYINT(1) DEFAULT 0 COMMENT 'Divorced status'",
                'spouse_deceased': "ALTER TABLE families ADD COLUMN spouse_deceased TINYINT(1) DEFAULT 0 COMMENT 'Widowed status'",
                'is_association_member': "ALTER TABLE families ADD COLUMN is_association_member TINYINT(1) DEFAULT 0 COMMENT 'Association member'",
            }
            
            # Define expected columns for members table
            members_columns = {
                'mother_name': "ALTER TABLE members ADD COLUMN mother_name VARCHAR(100) COMMENT 'Mother name' AFTER last_name",
                'is_deceased': "ALTER TABLE members ADD COLUMN is_deceased TINYINT(1) DEFAULT 0 COMMENT 'Deceased status'",
                'is_disabled': "ALTER TABLE members ADD COLUMN is_disabled TINYINT(1) DEFAULT 0 COMMENT 'Disabled status'",
            }
            
            # Define expected columns for app_settings table
            settings_columns = {
                'subscriptions_visible_columns': "ALTER TABLE app_settings ADD COLUMN subscriptions_visible_columns TEXT COMMENT 'JSON array of visible columns for subscriptions'",
                'subscriptions_columns_locked': "ALTER TABLE app_settings ADD COLUMN subscriptions_columns_locked TINYINT(1) DEFAULT 0 COMMENT 'Lock columns for subscriptions'",
            }
            
            # Check and fix families columns
            for col_name, alter_sql in families_columns.items():
                if not self._column_exists(connection, 'families', col_name):
                    logger.info(f"Adding missing column: families.{col_name}")
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(alter_sql)
                        connection.commit()
                        fixed_count += 1
                        logger.info(f"Successfully added column: families.{col_name}")
                    except Exception as e:
                        logger.error(f"Failed to add column families.{col_name}: {e}")
            
            # Check and fix members columns
            for col_name, alter_sql in members_columns.items():
                if not self._column_exists(connection, 'members', col_name):
                    logger.info(f"Adding missing column: members.{col_name}")
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(alter_sql)
                        connection.commit()
                        fixed_count += 1
                        logger.info(f"Successfully added column: members.{col_name}")
                    except Exception as e:
                        logger.error(f"Failed to add column members.{col_name}: {e}")
            
            # Check and fix app_settings columns
            for col_name, alter_sql in settings_columns.items():
                if not self._column_exists(connection, 'app_settings', col_name):
                    logger.info(f"Adding missing column: app_settings.{col_name}")
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(alter_sql)
                        connection.commit()
                        fixed_count += 1
                        logger.info(f"Successfully added column: app_settings.{col_name}")
                    except Exception as e:
                        logger.error(f"Failed to add column app_settings.{col_name}: {e}")
            
            return fixed_count
            
        except Exception as e:
            logger.error(f"Error checking/fixing missing columns: {e}")
            return fixed_count
    
    def _column_exists(self, connection, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.columns 
                    WHERE table_schema = DATABASE() 
                    AND table_name = %s 
                    AND column_name = %s
                """, (table_name, column_name))
                result = cursor.fetchone()
                return result and result['count'] > 0
        except Exception as e:
            logger.error(f"Error checking column existence: {e}")
            return False
    
    def _pick_accent_color(self):
        """Open a color picker for the receipt/invoice accent color."""
        from PySide6.QtGui import QColor
        cur = (self.pdf_accent_color_input.text() or '').strip() or '#1565C0'
        try:
            initial = QColor(cur)
        except Exception:
            initial = QColor('#1565C0')
        col = QColorDialog.getColor(initial, self, "Επιλογή χρώματος")
        if col.isValid():
            self.pdf_accent_color_input.setText(col.name().upper())

    def _open_pdf_editor(self, template_type: str, template_name: str):
        """Open the PDF template editor dialog."""
        try:
            from ui.widgets.pdf_template_editor import PDFTemplateEditorDialog
            
            # Get database connection from settings_service
            connection = self.settings_service.db_connection.get_connection()
            
            dialog = PDFTemplateEditorDialog(
                template_type=template_type,
                template_name=template_name,
                db_connection=connection,
                settings_service=self.settings_service,
                parent=self
            )
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Failed to open PDF editor: {e}")
            QMessageBox.critical(
                self,
                "Σφάλμα",
                f"Αποτυχία ανοίγματος του PDF editor:\n{str(e)}"
            )

    def _create_users_tab(self):
        """Deprecated: user management moved to the dedicated «Χρήστες» nav screen.
        Kept as a no-op so nothing breaks if referenced."""
        return
