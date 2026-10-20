# -*- coding: utf-8 -*-
"""
About Dialog
Professional about dialog with company information and logo.
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextBrowser, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from utils.resource_loader import app_icon, main_logo

logger = logging.getLogger(__name__)


class AboutDialog(QDialog):
    """Professional about dialog with company information."""
    
    def __init__(self, parent=None):
        """
        Initialize AboutDialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._init_ui()
        
        logger.debug("AboutDialog initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Σχετικά με το Support CRM")
        self.setWindowIcon(app_icon())
        self.setMinimumWidth(650)
        self.setMinimumHeight(600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with logo
        header_layout = self._create_header()
        layout.addLayout(header_layout)
        
        # Content area with scrollable text
        content = self._create_content()
        layout.addWidget(content)
        
        # Footer with close button
        footer_layout = self._create_footer()
        layout.addLayout(footer_layout)
    
    def _create_header(self) -> QVBoxLayout:
        """Create the header with logo and title."""
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(20, 20, 20, 10)
        header_layout.setSpacing(10)
        
        # Logo
        logo_label = QLabel()
        logo_pixmap = main_logo(width=150)
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(logo_label)
        
        # Title
        title_label = QLabel("Support CRM")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Customer Support Management System")
        subtitle_font = QFont()
        subtitle_font.setPointSize(11)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666;")
        header_layout.addWidget(subtitle_label)
        
        # Version
        import config
        version_label = QLabel(f"Έκδοση {config.APP_VERSION}")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #888; margin-top: 5px;")
        header_layout.addWidget(version_label)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #ddd;")
        header_layout.addWidget(separator)
        
        return header_layout
    
    def _create_content(self) -> QTextBrowser:
        """Create the scrollable content area."""
        content = QTextBrowser()
        content.setOpenExternalLinks(True)
        content.setFrameShape(QFrame.NoFrame)
        content.setStyleSheet("""
            QTextBrowser {
                background-color: white;
                padding: 20px;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        
        # HTML content
        html_content = """
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.8;
            }
            h2 {
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 8px;
                margin-top: 20px;
                margin-bottom: 15px;
            }
            h3 {
                color: #34495e;
                margin-top: 15px;
                margin-bottom: 10px;
            }
            p {
                margin: 10px 0;
                text-align: justify;
            }
            ul {
                margin: 10px 0;
                padding-left: 25px;
            }
            li {
                margin: 5px 0;
            }
            .info-box {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
            }
            .copyright {
                background-color: #ecf0f1;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                font-size: 12px;
                color: #555;
                line-height: 1.6;
            }
            a {
                color: #3498db;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
        
        <h2>📌 Τίτλος</h2>
        <p><strong>Support CRM</strong></p>
        
        <h2>📄 Περιγραφή</h2>
        <p>
            Το <strong>Support CRM</strong> είναι μια desktop εφαρμογή διαχείρισης πελατών 
            και υποστήριξης, σχεδιασμένη για την οργάνωση τεχνικών συνδέσεων, συνεδριών 
            υποστήριξης και βασικών στοιχείων πελατών, με έμφαση στην απλότητα και την 
            αποδοτικότητα.
        </p>
        
        <h2>🔧 Λειτουργίες</h2>
        <ul>
            <li>Διαχείριση πελατών και στοιχείων επικοινωνίας</li>
            <li>Ενσωμάτωση απομακρυσμένης υποστήριξης μέσω RustDesk (public servers)</li>
            <li>One-click σύνδεση με πελάτη</li>
            <li>Βασική καταγραφή συνεδριών υποστήριξης</li>
            <li>Φιλικό και επεκτάσιμο γραφικό περιβάλλον (GUI)</li>
        </ul>
        
        <h2>🎓 Σκοπός</h2>
        <p>
            Η εφαρμογή αναπτύχθηκε στο πλαίσιο πανεπιστημιακής εργασίας με στόχο την 
            κατανόηση του σχεδιασμού desktop εφαρμογών, της διαχείρισης GUI layouts και 
            της ενσωμάτωσης εξωτερικών εργαλείων υποστήριξης.
        </p>
        
        <h2>⚖️ Πνευματικά Δικαιώματα</h2>
        <div class="copyright">
            <p><strong>© 2026 Αναγνωστόπουλος Φίλιππος</strong></p>
            <p>
                Το λογισμικό <strong>Support CRM</strong> αναπτύχθηκε για εκπαιδευτικούς 
                σκοπούς στο πλαίσιο πανεπιστημιακής εργασίας.
            </p>
            <p>
                Ο πηγαίος κώδικας και ο σχεδιασμός της εφαρμογής αποτελούν πνευματική 
                ιδιοκτησία του δημιουργού.
            </p>
            <p>
                Η εφαρμογή χρησιμοποιεί το <strong>RustDesk</strong> ως εξωτερικό εργαλείο 
                απομακρυσμένης πρόσβασης. Το RustDesk αποτελεί ανεξάρτητο λογισμικό ανοικτού 
                κώδικα και διέπεται από τη δική του άδεια χρήσης.
            </p>
            <p>
                <strong>Δεν παρέχεται καμία εγγύηση για εμπορική χρήση.</strong>
            </p>
        </div>
        """
        
        content.setHtml(html_content)
        
        return content
    
    def _create_footer(self) -> QHBoxLayout:
        """Create the footer with close button."""
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(20, 10, 20, 20)
        
        footer_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Κλείσιμο")
        close_btn.setMinimumWidth(100)
        close_btn.setMinimumHeight(32)
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        footer_layout.addWidget(close_btn)
        
        return footer_layout
