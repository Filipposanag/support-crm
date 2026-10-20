# -*- coding: utf-8 -*-
"""
Document type selection (Απόδειξη / Τιμολόγιο) + issue helper.

Reused by session end, package purchase and the manual buttons in
Πληρωμές / Συνδρομές. Keeps issuing logic in one place.
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QRadioButton,
    QButtonGroup, QFrame, QWidget, QLineEdit, QDialogButtonBox,
    QMessageBox, QFileDialog, QTextEdit,
)
from ui.utils.ui_helpers import gr_question

logger = logging.getLogger(__name__)


class DocumentTypeDialog(QDialog):
    """Ask whether to issue a Receipt (Απόδειξη) or Invoice (Τιμολόγιο)."""

    def __init__(self, parent=None, default_afm: str = '', default_doy: str = ''):
        super().__init__(parent)
        self.setWindowTitle("Τύπος παραστατικού")
        self.setMinimumWidth(460)

        self.document_type = 'receipt'
        self.afm = ''
        self.doy = ''
        self.notes = ''

        self.setStyleSheet(
            "QRadioButton::indicator{width:16px;height:16px;}"
            "QRadioButton::indicator:unchecked{border:2px solid #B0BAC5;border-radius:9px;background:#ffffff;}"
            "QRadioButton::indicator:checked{border:2px solid #1565C0;border-radius:9px;background:#1565C0;}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(12)

        heading = QLabel("Τι θέλει ο πελάτης;")
        heading.setStyleSheet("font-size:15px;font-weight:600;")
        root.addWidget(heading)

        self.group = QButtonGroup(self)
        self.card_receipt, self.rb_receipt = self._make_card(
            "Απόδειξη Παροχής Υπηρεσιών", "Για ιδιώτες — δεν χρειάζεται ΑΦΜ.")
        self.card_invoice, self.rb_invoice = self._make_card(
            "Τιμολόγιο Παροχής Υπηρεσιών", "Για επιχείρηση / επαγγελματία — απαιτείται ΑΦΜ.")
        self.group.addButton(self.rb_receipt)
        self.group.addButton(self.rb_invoice)
        root.addWidget(self.card_receipt)
        root.addWidget(self.card_invoice)

        # ΑΦΜ (invoice only)
        self.tax_box = QWidget()
        tl = QFormLayout(self.tax_box)
        tl.setContentsMargins(6, 4, 6, 0)
        self.afm_input = QLineEdit(default_afm or '')
        self.afm_input.setPlaceholderText("π.χ. 801234567")
        tl.addRow("ΑΦΜ:", self.afm_input)
        root.addWidget(self.tax_box)
        self.tax_box.setVisible(False)

        # Optional technician comments about the work — printed on the document
        self.notes_label = QLabel("Σχόλια για τη δουλειά (προαιρετικά):")
        self.notes_label.setStyleSheet("font-size:12px;color:#3A4550;margin-top:4px;")
        root.addWidget(self.notes_label)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText(
            "π.χ. Καθαρισμός συστήματος, εγκατάσταση antivirus, αντικατάσταση δίσκου…\n"
            "Ό,τι γράψετε εδώ θα εμφανιστεί στην απόδειξη / το τιμολόγιο.")
        self.notes_input.setFixedHeight(70)
        root.addWidget(self.notes_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Έκδοση")
        buttons.button(QDialogButtonBox.Cancel).setText("Άκυρο")
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.rb_receipt.toggled.connect(self._update)
        self.rb_invoice.toggled.connect(self._update)
        self.rb_receipt.setChecked(True)
        self._update()

    def _make_card(self, title, subtitle):
        card = QFrame()
        card.setObjectName("card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 11, 14, 11)
        lay.setSpacing(12)
        rb = QRadioButton()
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet("font-weight:600;font-size:13px;")
        sub = QLabel(subtitle)
        sub.setStyleSheet("color:#6B7785;font-size:11px;")
        col.addWidget(t)
        col.addWidget(sub)
        lay.addWidget(rb, 0, Qt.AlignVCenter)
        lay.addLayout(col, 1)
        card.mousePressEvent = lambda e, _rb=rb: _rb.setChecked(True)
        return card, rb

    def _update(self, *_):
        self.tax_box.setVisible(self.rb_invoice.isChecked())
        for card, rb in ((self.card_receipt, self.rb_receipt),
                         (self.card_invoice, self.rb_invoice)):
            sel = rb.isChecked()
            border = "#1565C0" if sel else "#D8DEE6"
            bg = "#EAF2FB" if sel else "#FFFFFF"
            card.setStyleSheet("#card{border:2px solid %s;border-radius:8px;background:%s;}" % (border, bg))
        self.adjustSize()

    def _on_ok(self):
        if self.rb_invoice.isChecked():
            afm = self.afm_input.text().strip()
            if not afm:
                QMessageBox.warning(self, "ΑΦΜ",
                                    "Για την έκδοση τιμολογίου απαιτείται ο ΑΦΜ του πελάτη.")
                return
            self.document_type = 'invoice'
            self.afm = afm
            self.doy = ''
        else:
            self.document_type = 'receipt'
        self.notes = self.notes_input.toPlainText().strip()
        self.accept()


def issue_document(parent, payment_id, *, payments_repo, receipt_service,
                   settings_service, auto_numbering_service, clients_repo=None,
                   client_id=None, client_name='', default_afm='', default_doy=''):
    """
    Show the type dialog and issue the chosen document as a PDF.

    Returns the saved file path, or None if the user cancelled or it failed.
    """
    dlg = DocumentTypeDialog(parent, default_afm=default_afm, default_doy=default_doy)
    if dlg.exec() != QDialog.Accepted:
        return None

    doc_type = dlg.document_type
    afm, doy = dlg.afm, dlg.doy
    notes = (getattr(dlg, 'notes', '') or '').strip()

    # settings + VAT snapshot
    settings = settings_service.get_all_settings() or settings_service.load_settings()
    try:
        vat_rate = float(getattr(settings, 'vat_rate', 0) or 0)
    except (TypeError, ValueError):
        vat_rate = 0.0
    rec_prefix = getattr(settings, 'receipt_prefix', '') or 'ΑΠ'
    inv_prefix = getattr(settings, 'invoice_prefix', '') or 'ΤΠΥ'

    # remember client's tax info for next time
    if doc_type == 'invoice' and clients_repo is not None and client_id:
        try:
            _upd = {'afm': afm}
            if doy:
                _upd['doy'] = doy
            clients_repo.update_client(client_id, _upd)
        except Exception as e:
            logger.warning(f"Could not save client tax info: {e}")

    # numbering (keep existing number if it already matches the requested type)
    payment = payments_repo.get_payment_with_family(payment_id) or {}
    cur = payment.get('receipt_no') or ''
    try:
        if doc_type == 'invoice':
            number = cur if cur.startswith(inv_prefix + '-') else auto_numbering_service.get_next_invoice_number()
        else:
            number = cur if cur.startswith(rec_prefix + '-') else auto_numbering_service.get_next_receipt_number()
    except Exception as e:
        logger.error(f"Numbering failed: {e}")
        number = cur or ''

    # persist document info on the payment
    try:
        payments_repo.set_document_info(payment_id, doc_type, number, vat_rate,
                                        document_notes=(notes or None))
    except Exception as e:
        logger.error(f"Failed to persist document info: {e}")
        QMessageBox.critical(parent, "Σφάλμα",
                             f"Αποτυχία αποθήκευσης στοιχείων παραστατικού:\n{e}")
        return None

    # choose save location
    label = 'Τιμολόγιο' if doc_type == 'invoice' else 'Απόδειξη'
    safe = "".join(ch for ch in (client_name or '') if ch.isalnum() or ch in (' ', '_')).strip().replace(' ', '_')
    default_name = f"{label}_{(number or str(payment_id)).replace('/', '-')}_{safe}.pdf"
    # Default to the dedicated folder: Τιμολόγια for invoices, Αποδείξεις for receipts.
    try:
        from config import ensure_document_dirs
        _inv_dir, _rec_dir = ensure_document_dirs()
        _target_dir = _inv_dir if doc_type == 'invoice' else _rec_dir
        default_filename = str(_target_dir / default_name)
    except Exception as e:
        logger.warning(f"Could not resolve document folder, using name only: {e}")
        default_filename = default_name
    file_path, _ = QFileDialog.getSaveFileName(parent, f"Αποθήκευση: {label}",
                                               default_filename, "PDF Files (*.pdf)")
    if not file_path:
        return None
    if not file_path.lower().endswith('.pdf'):
        file_path += '.pdf'

    try:
        receipt_service.generate_document_pdf(payment_id, file_path, doc_type)
    except Exception as e:
        logger.error(f"Failed to generate document PDF: {e}", exc_info=True)
        QMessageBox.critical(parent, "Σφάλμα", f"Αποτυχία δημιουργίας PDF:\n{e}")
        return None

    # offer to open
    reply = gr_question(
        parent, "Επιτυχία",
        f"Το {label.lower()} δημιουργήθηκε:\n{file_path}\n\nΘέλετε να το ανοίξετε;",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
    )
    if reply == QMessageBox.Yes:
        try:
            import os
            os.startfile(file_path)  # Windows
        except Exception as e:
            logger.warning(f"Could not open PDF: {e}")

    return file_path


def issue_document_from_db(parent, payment_id, db, *, clients_repo=None,
                           client_id=None, client_name='', default_afm='', default_doy=''):
    """
    Convenience wrapper: build the needed services from a DB connection and
    issue a document. Client name/id/ΑΦΜ/ΔΟΥ default from the payment record.
    """
    from db.repositories.payments_repo import PaymentsRepository
    from services.settings_service import SettingsService
    from services.receipt_service import ReceiptService
    from services.auto_numbering_service import AutoNumberingService

    payments_repo = PaymentsRepository(db)
    settings_service = SettingsService(db)
    receipt_service = ReceiptService(payments_repo, settings_service)
    auto_numbering_service = AutoNumberingService(db)

    try:
        pay = payments_repo.get_payment_with_family(payment_id) or {}
    except Exception:
        pay = {}
    if not client_name:
        client_name = pay.get('company_name') or pay.get('family_name') or ''
    if client_id is None:
        client_id = pay.get('family_id')
    if not default_afm:
        default_afm = pay.get('afm') or ''
    if not default_doy:
        default_doy = pay.get('doy') or ''

    return issue_document(
        parent, payment_id,
        payments_repo=payments_repo, receipt_service=receipt_service,
        settings_service=settings_service, auto_numbering_service=auto_numbering_service,
        clients_repo=clients_repo, client_id=client_id, client_name=client_name,
        default_afm=default_afm, default_doy=default_doy,
    )
