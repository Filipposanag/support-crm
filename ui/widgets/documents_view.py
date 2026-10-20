# -*- coding: utf-8 -*-
"""
Παραστατικά — list of issued documents (receipts & invoices).

Shows every payment that has an issued document number, with type, date,
client and amounts, and lets the user re-open/re-print the PDF.
"""

import logging

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFileDialog, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QDoubleSpinBox, QDateEdit, QCheckBox, QDialogButtonBox, QCompleter,
)
from ui.utils.ui_helpers import gr_question
from services.audit_context import log_audit
from ui.utils.permission_helper import has_permission

logger = logging.getLogger(__name__)


class DocumentsView(QWidget):
    """Read-only list of issued receipts/invoices with re-print."""

    def __init__(self, db_connection, clients_repo=None, tr_manager=None, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.clients_repo = clients_repo
        self.tr_manager = tr_manager
        self._rows = []
        self._build()
        self.load()

    # ---------------------------------------------------------------- UI
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Παραστατικά")
        title.setStyleSheet("font-size:20px;font-weight:700;")
        layout.addWidget(title)

        self.summary = QLabel("")
        self.summary.setStyleSheet("color:#6B7785;font-size:12px;")
        layout.addWidget(self.summary)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        bar.addWidget(QLabel("Αναζήτηση:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Όνομα ή κωδικός πελάτη, αρ. παραστατικού…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(260)
        self.search_input.textChanged.connect(self._populate)
        bar.addWidget(self.search_input)
        bar.addWidget(QLabel("Τύπος:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Όλα", "all")
        self.filter_combo.addItem("Αποδείξεις", "receipt")
        self.filter_combo.addItem("Τιμολόγια", "invoice")
        self.filter_combo.currentIndexChanged.connect(self._populate)
        bar.addWidget(self.filter_combo)
        self.new_btn = QPushButton("➕  Νέο παραστατικό")
        self.new_btn.clicked.connect(self._new_document)
        self.new_btn.setEnabled(has_permission('payments.create'))
        bar.addWidget(self.new_btn)
        bar.addStretch(1)
        self.open_btn = QPushButton("Άνοιγμα / Επανέκδοση PDF")
        self.open_btn.clicked.connect(self._reissue_selected)
        bar.addWidget(self.open_btn)
        self.email_btn = QPushButton("✉  Αποστολή με email")
        self.email_btn.clicked.connect(self._email_selected)
        bar.addWidget(self.email_btn)
        self.refresh_btn = QPushButton("↻ Ανανέωση")
        self.refresh_btn.clicked.connect(self.load)
        bar.addWidget(self.refresh_btn)
        layout.addLayout(bar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Αριθμός", "Τύπος", "Ημ/νία", "Πελάτης", "Καθαρή αξία", "ΦΠΑ", "Σύνολο"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._reissue_selected)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        for col in (0, 1, 2, 4, 5, 6):
            hh.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    # ------------------------------------------------------------- data
    def load(self):
        try:
            rows = self.db.execute_query(
                "SELECT p.id, p.receipt_no, p.document_type, p.payment_date, "
                "       p.paid_amount, p.total_amount, p.vat_rate, "
                "       f.legacy_code AS legacy_code, "
                "       COALESCE(NULLIF(f.company_name,''), "
                "                TRIM(CONCAT(COALESCE(f.last_name,''),' ',COALESCE(f.first_name,'')))) AS client "
                "FROM payments p LEFT JOIN families f ON p.family_id=f.id "
                "WHERE p.receipt_no IS NOT NULL AND p.receipt_no<>'' "
                "ORDER BY p.payment_date DESC, p.id DESC"
            ) or []
        except Exception as e:
            logger.error(f"Failed to load documents: {e}")
            rows = []
        self._rows = rows
        self._populate()

    def _populate(self):
        flt = self.filter_combo.currentData() if hasattr(self, 'filter_combo') else "all"
        query = (self.search_input.text().strip().lower()
                 if hasattr(self, 'search_input') else "")
        shown = []
        total_sum = 0.0
        self.table.setRowCount(0)
        for r in self._rows:
            dtype = (r.get('document_type') or 'receipt')
            if flt != "all" and dtype != flt:
                continue
            if query:
                haystack = " ".join([
                    str(r.get('client') or ''),
                    str(r.get('legacy_code') or ''),
                    str(r.get('receipt_no') or ''),
                ]).lower()
                if query not in haystack:
                    continue
            shown.append(r)

        for r in shown:
            dtype = (r.get('document_type') or 'receipt')
            gross = self._f(r.get('paid_amount')) or self._f(r.get('total_amount'))
            vat_rate = self._f(r.get('vat_rate'))
            if vat_rate > 0:
                net = gross / (1 + vat_rate / 100.0)
                vat_amt = gross - net
            else:
                net, vat_amt = gross, 0.0
            total_sum += gross

            row = self.table.rowCount()
            self.table.insertRow(row)
            cells = [
                (r.get('receipt_no') or '—', Qt.AlignLeft),
                ("Τιμολόγιο" if dtype == 'invoice' else "Απόδειξη", Qt.AlignCenter),
                (self._fmt_date(r.get('payment_date')), Qt.AlignCenter),
                (r.get('client') or '', Qt.AlignLeft),
                (f"{net:.2f} €", Qt.AlignRight),
                (f"{vat_amt:.2f} €", Qt.AlignRight),
                (f"{gross:.2f} €", Qt.AlignRight),
            ]
            for col, (val, align) in enumerate(cells):
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(align | Qt.AlignVCenter)
                if col == 0:
                    it.setData(Qt.UserRole, r.get('id'))
                    it.setData(Qt.UserRole + 1, dtype)
                self.table.setItem(row, col, it)

        self.summary.setText(f"{len(shown)} παραστατικά  ·  Σύνολο: {total_sum:.2f} €")

    # --------------------------------------------------------- new doc
    def _new_document(self):
        if not has_permission('payments.create'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα έκδοσης παραστατικού.")
            return
        """Issue a receipt/invoice WITHOUT a session (ad-hoc charge)."""
        dlg = NewDocumentDialog(self.db, self.clients_repo, self)
        if dlg.exec() != QDialog.Accepted:
            return
        info = dlg.result_data()
        if not info:
            return
        try:
            amount = float(info['amount'])
            paid = amount if info['paid'] else 0.0
            remaining = 0.0 if info['paid'] else amount
            status = 'paid' if info['paid'] else 'unpaid'
            d = info['date']
            year = d.year if hasattr(d, 'year') else None
            pay_id = self.db.execute_update(
                "INSERT INTO payments (family_id, payment_date, description, "
                "total_amount, paid_amount, remaining_amount, status, year) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (info['client_id'], d, info['description'], amount, paid, remaining, status, year))
            self.db.commit()
            log_audit(self.db, 'payments', pay_id, 'INSERT', None,
                      {'family_id': info['client_id'], 'description': info['description'],
                       'amount': amount, 'status': status})
        except Exception as e:
            logger.error(f"create ad-hoc payment failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία δημιουργίας παραστατικού:\n{e}")
            return
        try:
            from ui.widgets.document_type_dialog import issue_document_from_db
            issue_document_from_db(self, pay_id, self.db,
                                   clients_repo=self.clients_repo,
                                   client_id=info['client_id'],
                                   client_name=info['client_name'],
                                   default_afm=info.get('afm', ''))
        except Exception as e:
            logger.warning(f"issue after new document failed: {e}")
        self.load()

    # --------------------------------------------------------- re-issue
    def _reissue_selected(self, *_):
        if not has_permission('payments.view'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα προβολής παραστατικών.")
            return
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Παραστατικά", "Επιλέξτε ένα παραστατικό από τη λίστα.")
            return
        id_item = self.table.item(row, 0)
        if not id_item:
            return
        payment_id = id_item.data(Qt.UserRole)
        dtype = id_item.data(Qt.UserRole + 1) or 'receipt'
        number = id_item.text()
        if not payment_id:
            return

        label = 'Τιμολόγιο' if dtype == 'invoice' else 'Απόδειξη'
        client = self.table.item(row, 3).text() if self.table.item(row, 3) else ''
        safe = "".join(ch for ch in client if ch.isalnum() or ch in (' ', '_')).strip().replace(' ', '_')
        default_name = f"{label}_{str(number).replace('/', '-')}_{safe}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, f"Αποθήκευση: {label}",
                                                   default_name, "PDF Files (*.pdf)")
        if not file_path:
            return
        if not file_path.lower().endswith('.pdf'):
            file_path += '.pdf'

        try:
            from db.repositories.payments_repo import PaymentsRepository
            from services.settings_service import SettingsService
            from services.receipt_service import ReceiptService
            pr = PaymentsRepository(self.db)
            ss = SettingsService(self.db)
            rs = ReceiptService(pr, ss)
            rs.generate_document_pdf(payment_id, file_path, dtype)
        except Exception as e:
            logger.error(f"Re-issue failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία δημιουργίας PDF:\n{e}")
            return

        if gr_question(self, "Επιτυχία",
                                f"Δημιουργήθηκε:\n{file_path}\n\nΆνοιγμα;",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) == QMessageBox.Yes:
            try:
                import os
                os.startfile(file_path)
            except Exception as e:
                logger.warning(f"Could not open PDF: {e}")

    def _email_selected(self, *_):
        if not has_permission('payments.create'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα αποστολής παραστατικού.")
            return
        """Send the selected document's PDF to the client's email."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Παραστατικά", "Επιλέξτε ένα παραστατικό από τη λίστα.")
            return
        id_item = self.table.item(row, 0)
        if not id_item:
            return
        payment_id = id_item.data(Qt.UserRole)
        dtype = id_item.data(Qt.UserRole + 1) or 'receipt'
        number = id_item.text()
        client = self.table.item(row, 3).text() if self.table.item(row, 3) else ''
        if not payment_id:
            return

        # fetch client email + amounts for this document
        try:
            _r = self.db.execute_query(
                "SELECT f.email AS email, p.paid_amount, p.total_amount, p.payment_date "
                "FROM payments p LEFT JOIN families f ON p.family_id=f.id WHERE p.id=%s",
                (payment_id,))
        except Exception as e:
            logger.error(f"Email lookup failed: {e}")
            _r = None
        if not _r:
            QMessageBox.critical(self, "Σφάλμα", "Δεν βρέθηκαν στοιχεία για το παραστατικό.")
            return
        rec = _r[0]
        to_email = (rec.get('email') or '').strip()
        if not to_email:
            QMessageBox.warning(self, "Χωρίς email",
                                "Ο πελάτης δεν έχει email. Προσθέστε email στα στοιχεία του πελάτη.")
            return

        try:
            from db.repositories.payments_repo import PaymentsRepository
            from services.settings_service import SettingsService
            from services.receipt_service import ReceiptService
            from services.email_service import EmailService
            from ui.widgets.send_receipt_email_dialog import SendReceiptEmailDialog
            pr = PaymentsRepository(self.db)
            ss = SettingsService(self.db)
            rs = ReceiptService(pr, ss)
            email_service = EmailService(ss)
        except Exception as e:
            logger.error(f"Email services init failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Σφάλμα", f"Σφάλμα προετοιμασίας email:\n{e}")
            return

        if not email_service.is_configured():
            QMessageBox.warning(self, "Email",
                                "Το email δεν έχει ρυθμιστεί.\nΡυθμίστε το SMTP στις Ρυθμίσεις → «Email - Ειδοποιήσεις».")
            return

        # generate the PDF to a temporary file for the attachment
        import os as _os, tempfile as _tf
        label = 'Τιμολόγιο' if dtype == 'invoice' else 'Απόδειξη'
        safe = "".join(ch for ch in client if ch.isalnum() or ch in (' ', '_')).strip().replace(' ', '_')
        fname = f"{label}_{str(number).replace('/', '-')}_{safe}.pdf"
        pdf_path = _os.path.join(_tf.gettempdir(), fname)
        try:
            rs.generate_document_pdf(payment_id, pdf_path, dtype)
        except Exception as e:
            logger.error(f"PDF for email failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία δημιουργίας PDF:\n{e}")
            return

        def _f(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0
        pdate = rec.get('payment_date')
        if pdate and not isinstance(pdate, str):
            try:
                pdate = pdate.strftime('%d/%m/%Y')
            except Exception:
                pdate = str(pdate)
        payment_data = {
            'family_name': client,
            'payment_date': pdate or '',
            'amount': f"{(_f(rec.get('paid_amount')) or _f(rec.get('total_amount'))):.2f}",
            'receipt_no': number,
        }

        try:
            dlg = SendReceiptEmailDialog(email_service, ss, to_email, payment_data,
                                         pdf_path=pdf_path, parent=self)
            dlg.exec()
        except Exception as e:
            logger.error(f"Send email dialog failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Σφάλμα", f"Σφάλμα κατά την αποστολή:\n{e}")

    # ------------------------------------------------------------ utils
    @staticmethod
    def _f(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _fmt_date(d):
        if not d:
            return ''
        if isinstance(d, str):
            return d
        try:
            return d.strftime('%d/%m/%Y')
        except Exception:
            return str(d)


class NewDocumentDialog(QDialog):
    """Collect client + amount + description for an ad-hoc document."""

    def __init__(self, db, clients_repo=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.clients_repo = clients_repo
        self._data = None
        self.setWindowTitle("Νέο παραστατικό")
        self.setMinimumWidth(460)

        self._clients = self._load_clients()

        form = QFormLayout(self)
        form.setContentsMargins(20, 18, 20, 16)
        form.setSpacing(10)

        self.client_combo = QComboBox()
        self.client_combo.setEditable(True)
        self.client_combo.setInsertPolicy(QComboBox.NoInsert)
        for cid, label, afm in self._clients:
            self.client_combo.addItem(label, (cid, afm))
        self.client_combo.setCurrentIndex(-1)
        self.client_combo.lineEdit().setPlaceholderText("Πληκτρολογήστε όνομα...")
        comp = QCompleter([lbl for _, lbl, _ in self._clients], self)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        self.client_combo.setCompleter(comp)
        form.addRow("Πελάτης *:", self.client_combo)

        self.desc_input = QLineEdit("Υπηρεσίες τεχνικής υποστήριξης")
        form.addRow("Περιγραφή:", self.desc_input)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0, 1000000)
        self.amount_input.setDecimals(2)
        self.amount_input.setSuffix(" €")
        form.addRow("Ποσό (με ΦΠΑ):", self.amount_input)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        self.date_input.setDate(QDate.currentDate())
        form.addRow("Ημερομηνία:", self.date_input)

        self.paid_check = QCheckBox("Εξοφλημένο (αλλιώς περνά στις Οφειλές)")
        self.paid_check.setChecked(True)
        form.addRow("", self.paid_check)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Συνέχεια")
        btns.button(QDialogButtonBox.Cancel).setText("Άκυρο")
        btns.accepted.connect(self._ok)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _load_clients(self):
        rows = []
        try:
            data = None
            if self.clients_repo and hasattr(self.clients_repo, 'list_clients'):
                try:
                    data = self.clients_repo.list_clients(only_active=True, limit=5000)
                except Exception:
                    data = None
            if data is None:
                data = self.db.execute_query(
                    "SELECT id, last_name, first_name, company_name, afm FROM families "
                    "WHERE is_active=1 ORDER BY last_name, first_name") or []
            for r in data:
                name = ((r.get('company_name') or '').strip()
                        or ("%s %s" % (r.get('last_name', '') or '', r.get('first_name', '') or '')).strip())
                rows.append((r.get('id'), name, r.get('afm') or ''))
        except Exception as e:
            logger.error(f"load clients failed: {e}")
        return rows

    def _ok(self):
        cid = None
        afm = ''
        idx = self.client_combo.currentIndex()
        if idx >= 0 and self.client_combo.itemData(idx):
            cid, afm = self.client_combo.itemData(idx)
        else:
            typed = self.client_combo.currentText().strip()
            for i in range(self.client_combo.count()):
                if self.client_combo.itemText(i) == typed:
                    cid, afm = self.client_combo.itemData(i)
                    break
        if not cid:
            QMessageBox.warning(self, "Πελάτης", "Επιλέξτε πελάτη από τη λίστα.")
            return
        if self.amount_input.value() <= 0:
            QMessageBox.warning(self, "Ποσό", "Δώστε ποσό μεγαλύτερο του μηδενός.")
            return
        from datetime import date as _date
        qd = self.date_input.date()
        self._data = {
            'client_id': cid,
            'client_name': self.client_combo.currentText().strip(),
            'afm': afm,
            'description': self.desc_input.text().strip() or 'Υπηρεσίες τεχνικής υποστήριξης',
            'amount': self.amount_input.value(),
            'date': _date(qd.year(), qd.month(), qd.day()),
            'paid': self.paid_check.isChecked(),
        }
        self.accept()

    def result_data(self):
        return self._data
