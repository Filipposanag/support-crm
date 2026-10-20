# -*- coding: utf-8 -*-
"""
Client Packages / Expirations view.
Lists each client's active support-package assignment with expiry date and
remaining hours, and lets the user send a reminder email for a selected one.
Built on client_package_hours (same source the dashboard "Πακέτα που λήγουν" uses).
"""

import logging
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableView, QHeaderView, QAbstractItemView, QMessageBox,
    QDialog, QLineEdit, QTextEdit, QDialogButtonBox, QCheckBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor

from resources.icons import get_icon
from ui.utils.ui_helpers import fmt_hours_min
from ui.utils.permission_helper import has_permission

logger = logging.getLogger(__name__)


class _ReminderEmailDialog(QDialog):
    """Small editable dialog to send a subscription/package reminder email."""

    def __init__(self, email_service, to_email, subject, body, subscription_data, attachment_path=None, parent=None):
        super().__init__(parent)
        self.email_service = email_service
        self.subscription_data = subscription_data
        self.attachment_path = attachment_path
        self.setWindowTitle("Αποστολή Υπενθύμισης με Email")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Στοιχεία Email"))

        to_row = QHBoxLayout()
        to_row.addWidget(QLabel("Προς:"))
        self.to_edit = QLineEdit(to_email or "")
        self.to_edit.setPlaceholderText("email παραλήπτη")
        to_row.addWidget(self.to_edit)
        layout.addLayout(to_row)

        subj_row = QHBoxLayout()
        subj_row.addWidget(QLabel("Θέμα:"))
        self.subject_edit = QLineEdit(subject or "Υπενθύμιση Συνδρομής")
        subj_row.addWidget(self.subject_edit)
        layout.addLayout(subj_row)

        layout.addWidget(QLabel("Κείμενο:"))
        self.body_edit = QTextEdit()
        self.body_edit.setPlainText(body or "")
        self.body_edit.setMinimumHeight(180)
        layout.addWidget(self.body_edit)

        self.attach_cb = QCheckBox("Επισύναψη παραστατικού αγοράς (PDF)")
        self.attach_cb.setChecked(bool(self.attachment_path))
        self.attach_cb.setEnabled(bool(self.attachment_path))
        if not self.attachment_path:
            self.attach_cb.setToolTip("Δεν βρέθηκε παραστατικό αγοράς για αυτό το πακέτο.")
        layout.addWidget(self.attach_cb)

        buttons = QDialogButtonBox()
        send_btn = buttons.addButton("Αποστολή", QDialogButtonBox.AcceptRole)
        send_btn.setStyleSheet(
            "QPushButton{background-color:#1976D2;color:white;font-weight:bold;"
            "padding:8px 18px;border:none;border-radius:4px;}"
            "QPushButton:hover{background-color:#1565C0;}")
        buttons.addButton("Άκυρο", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self._send)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _send(self):
        recipient = self.to_edit.text().strip()
        subject = self.subject_edit.text().strip()
        body = self.body_edit.toPlainText().strip()

        if not recipient or "@" not in recipient or "." not in recipient.split("@")[-1]:
            QMessageBox.warning(self, "Προσοχή", "Δώστε έγκυρη διεύθυνση email παραλήπτη.")
            return
        if not subject or not body:
            QMessageBox.warning(self, "Προσοχή", "Το θέμα και το κείμενο δεν μπορούν να είναι κενά.")
            return
        if not self.email_service.is_configured():
            QMessageBox.warning(
                self, "Προσοχή",
                "Το email δεν έχει ρυθμιστεί. Ρυθμίστε το SMTP στις Ρυθμίσεις.")
            return
        try:
            attach = self.attachment_path if (self.attachment_path and self.attach_cb.isChecked()) else None
            ok = self.email_service.send_subscription_reminder_email(
                to_email=recipient,
                subscription_data=self.subscription_data,
                custom_subject=subject,
                custom_body=body,
                attachment_path=attach,
            )
        except Exception as e:
            logger.error(f"Reminder email failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία αποστολής:\n{e}")
            return
        if ok:
            QMessageBox.information(self, "Επιτυχία", f"Το email στάλθηκε στο {recipient}.")
            self.accept()
        else:
            QMessageBox.warning(self, "Σφάλμα", "Δεν ήταν δυνατή η αποστολή του email.")


class ClientPackagesView(QWidget):
    """List of client package assignments with expiry + reminder email."""

    def __init__(self, db_connection, settings_service, receipt_service=None, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.settings_service = settings_service
        self.receipt_service = receipt_service
        self._rows = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Λήξεις Πακέτων Πελατών")
        title.setStyleSheet("font-size:17px;font-weight:700;color:#1976D2;")
        layout.addWidget(title)
        hint = QLabel("Ενεργά πακέτα πελατών με ημερομηνία λήξης. Επιλέξτε έναν πελάτη "
                      "για να στείλετε υπενθύμιση με email.")
        hint.setStyleSheet("color:#607D8B;")
        layout.addWidget(hint)

        # filter row
        frow = QHBoxLayout()
        frow.addWidget(QLabel("Φίλτρο:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Όλα τα ενεργά", "all")
        self.filter_combo.addItem("Λήγουν σύντομα", "expiring")
        self.filter_combo.addItem("Ληγμένα", "expired")
        self.filter_combo.addItem("Χωρίς λήξη", "nolimit")
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        frow.addWidget(self.filter_combo)
        frow.addStretch()
        self.refresh_btn = QPushButton(get_icon('refresh'), "Ανανέωση")
        self.refresh_btn.clicked.connect(self.refresh)
        frow.addWidget(self.refresh_btn)
        layout.addLayout(frow)

        # table
        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(
            ["Πελάτης", "Πακέτο", "Υπόλοιπο ώρες", "Ημ. Λήξης", "Μέρες", "Κατάσταση"])
        self.table.setModel(self.model)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        for i, w in enumerate([220, 160, 130, 120, 90, 140]):
            hdr.resizeSection(i, w)
        hdr.setStretchLastSection(True)
        self.table.selectionModel = self.table.selectionModel
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table, stretch=1)

        # actions
        brow = QHBoxLayout()
        self.email_btn = QPushButton(get_icon('export'), "Αποστολή Υπενθύμισης Email")
        self.email_btn.setEnabled(False)
        self.email_btn.clicked.connect(self._on_send_reminder)
        self.email_btn.setStyleSheet(
            "QPushButton{background-color:#1976D2;color:white;font-weight:bold;"
            "padding:8px 16px;border:none;border-radius:4px;}"
            "QPushButton:hover{background-color:#1565C0;}"
            "QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        brow.addWidget(self.email_btn)
        brow.addStretch()
        layout.addLayout(brow)

    # ---- live refresh ----
    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.refresh()
        except Exception as e:
            logger.warning(f"Expirations auto-refresh failed: {e}")

    def _threshold_and_colors(self):
        days = 30
        c_exp, c_expired = "#EF6C00", "#C62828"
        try:
            s = self.settings_service.load_settings()
            days = int(getattr(s, 'days_before_expiration', 30) or 30)
            c_exp = getattr(s, 'color_expiring', None) or c_exp
            c_expired = getattr(s, 'color_expired', None) or c_expired
        except Exception as e:
            logger.debug(f"Using default expiry settings: {e}")
        return days, c_exp, c_expired

    def refresh(self):
        try:
            rows = self.db.execute_query(
                "SELECT cph.id, cph.payment_id AS payment_id, f.id AS cid, f.last_name, f.first_name, f.email, "
                "sp.name AS pkg_name, cph.remaining_hours AS rem, "
                "cph.expiry_date AS exp, "
                "DATEDIFF(cph.expiry_date, CURDATE()) AS days "
                "FROM client_package_hours cph "
                "JOIN families f ON cph.client_id = f.id "
                "JOIN support_packages sp ON cph.package_id = sp.id "
                "WHERE cph.is_active = 1 AND cph.remaining_hours > 0 "
                "ORDER BY (cph.expiry_date IS NULL), cph.expiry_date ASC"
            ) or []
        except Exception as e:
            logger.error(f"Error loading client packages: {e}")
            QMessageBox.critical(self, "Σφάλμα", f"Σφάλμα φόρτωσης:\n{e}")
            return
        self._rows = rows
        self._apply_filter()

    def _apply_filter(self):
        mode = self.filter_combo.currentData()
        days_thr, c_exp, c_expired = self._threshold_and_colors()
        self.model.removeRows(0, self.model.rowCount())

        for r in self._rows:
            exp = r.get('exp')
            days = r.get('days')
            days = int(days) if days is not None else None

            # classify
            if exp is None or days is None:
                state, color, mode_tag = "Χωρίς λήξη", "#607D8B", "nolimit"
            elif days < 0:
                state, color, mode_tag = "Ληγμένο", c_expired, "expired"
            elif days <= days_thr:
                state, color, mode_tag = "Λήγει σύντομα", c_exp, "expiring"
            else:
                state, color, mode_tag = "Ενεργό", "#2E7D32", "active"

            if mode == "expiring" and mode_tag != "expiring":
                continue
            if mode == "expired" and mode_tag != "expired":
                continue
            if mode == "nolimit" and mode_tag != "nolimit":
                continue

            name = f"{r.get('last_name','') or ''} {r.get('first_name','') or ''}".strip() or "—"
            name_item = QStandardItem(name)
            name_item.setData(r.get('id'), Qt.UserRole)          # cph id
            name_item.setData(r, Qt.UserRole + 1)                # full row

            pkg_item = QStandardItem(r.get('pkg_name', '') or "—")
            rem_item = QStandardItem(fmt_hours_min(r.get('rem')) if r.get('rem') is not None else "—")

            exp_s = exp.strftime('%d/%m/%Y') if hasattr(exp, 'strftime') else (str(exp) if exp else "—")
            exp_item = QStandardItem(exp_s)

            if days is None:
                days_txt = "—"
            elif days < 0:
                days_txt = f"πριν {abs(days)} μέρες"
            elif days == 0:
                days_txt = "σήμερα"
            else:
                days_txt = f"{days} μέρες"
            days_item = QStandardItem(days_txt)

            state_item = QStandardItem(state)
            state_item.setForeground(QColor(color))
            f = state_item.font(); f.setBold(True); state_item.setFont(f)

            self.model.appendRow([name_item, pkg_item, rem_item, exp_item, days_item, state_item])

    def _selected_row(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        return self.model.item(sel[0].row(), 0).data(Qt.UserRole + 1)

    def _on_selection_changed(self):
        self.email_btn.setEnabled(
            self.table.selectionModel().hasSelection() and has_permission('packages.view'))

    def _on_send_reminder(self):
        if not has_permission('packages.view'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                                "Δεν έχετε δικαίωμα για αυτή την ενέργεια.")
            return
        row = self._selected_row()
        if not row:
            return
        email = (row.get('email') or '').strip()
        if not email:
            QMessageBox.warning(
                self, "Χωρίς email",
                "Ο πελάτης δεν έχει καταχωρημένο email. Προσθέστε το στα στοιχεία του πελάτη.")
            return

        exp = row.get('exp')
        exp_s = exp.strftime('%d/%m/%Y') if hasattr(exp, 'strftime') else (str(exp) if exp else '')
        name = f"{row.get('last_name','') or ''} {row.get('first_name','') or ''}".strip()

        # Build services + prefilled template
        from services.email_service import EmailService
        email_service = EmailService(self.settings_service)
        try:
            cfg = self.settings_service.get_email_subscription_config()
        except Exception:
            cfg = {}
        subject = cfg.get('subject', 'Υπενθύμιση Συνδρομής')
        body_tpl = cfg.get('body', 'Σας υπενθυμίζουμε ότι η συνδρομή σας λήγει.')
        try:
            body = body_tpl.format(family_name=name, client_name=name, expiry_date=exp_s,
                                   total_amount='', paid_amount='', remaining_amount='',
                                   org_name=self.settings_service.get_org_name())
        except Exception:
            body = body_tpl

        sub_data = {'family_name': name, 'client_name': name, 'expiry_date': exp_s,
                    'total_amount': '', 'paid_amount': '', 'remaining_amount': ''}

        # Attach the purchase receipt (the document created when the package was bought)
        pdf_path = None
        pay_id = row.get('payment_id')
        if pay_id and self.receipt_service is not None:
            try:
                import tempfile, os
                dtype = 'receipt'
                try:
                    _r = self.db.execute_query(
                        "SELECT document_type FROM payments WHERE id=%s", (pay_id,))
                    if _r and _r[0].get('document_type'):
                        dtype = _r[0]['document_type']
                except Exception:
                    pass
                pdf_path = os.path.join(tempfile.gettempdir(), f"doc_{pay_id}.pdf")
                self.receipt_service.generate_document_pdf(int(pay_id), pdf_path, dtype)
            except Exception as e:
                logger.warning(f"Could not generate purchase receipt PDF: {e}")
                pdf_path = None

        dlg = _ReminderEmailDialog(email_service, email, subject, body, sub_data, pdf_path, self)
        dlg.exec()
