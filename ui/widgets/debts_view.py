# -*- coding: utf-8 -*-
"""
Debts View - Οθόνη Οφειλών
Aggregated outstanding balances per client, with quick actions.
Συγκεντρωτική προβολή εκκρεμών οφειλών ανά πελάτη με γρήγορες ενέργειες.

Self-contained: reads live data via db_connection.execute_query() (same pattern
as DashboardView). Reuses PaymentForm, ClientCardDialog and RustDeskService.
"""

import logging
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QLineEdit, QCheckBox, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog, QAbstractItemView,
    QDialog, QFormLayout, QDoubleSpinBox, QDialogButtonBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from ui.utils.permission_helper import has_permission

logger = logging.getLogger(__name__)

# Days after which an outstanding payment is considered overdue.
OVERDUE_DAYS = 30

_PLAN_LABELS = {
    "hourly": "Ωριαία",
    "monthly": "Μηνιαία",
    "yearly": "Ετήσια",
    "custom": "Προσαρμοσμένο",
}


class DebtsView(QWidget):
    """Outstanding-balances screen (Οθόνη Οφειλών)."""

    def __init__(self, db_connection, families_repo, clients_repo,
                 rustdesk_service=None, tr_manager=None, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.families_repo = families_repo
        self.clients_repo = clients_repo
        self.rustdesk_service = rustdesk_service
        self.tr_manager = tr_manager

        # filter state
        self.search_text = ""
        self.min_amount = 0.0
        self.only_overdue = False
        self.sort_mode = "amount"  # amount | age | name

        self._rows_cache = []  # last loaded rows (list of dict)
        self._kpi_labels = {}

        self._build_ui()
        self.refresh()
        logger.debug("DebtsView initialized")

    # ---------- data helpers ----------
    def _query(self, sql, params=None, default=None):
        try:
            rows = self.db.execute_query(sql, params)
            return rows if rows is not None else (default or [])
        except Exception as e:
            logger.error(f"Debts query failed: {e}")
            return default if default is not None else []

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title = QLabel("Οφειλές Πελατών")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #C62828;")
        header.addWidget(title)
        header.addStretch()
        self.export_btn = QPushButton("Εξαγωγή σε Excel")
        self.export_btn.setStyleSheet("QPushButton{background-color:#4CAF50;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#45a049;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        self.export_btn.clicked.connect(self._on_export)
        self.export_btn.setEnabled(has_permission('payments.export'))
        header.addWidget(self.export_btn)
        self.refresh_btn = QPushButton("Ανανέωση")
        self.refresh_btn.setStyleSheet("QPushButton{background-color:#1976D2;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#1565C0;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)
        root.addLayout(header)

        # KPI cards
        kpi = QGridLayout()
        kpi.setSpacing(12)
        cards = [
            ("total", "Συνολικές Οφειλές", "#C62828"),
            ("clients", "Πελάτες με Οφειλή", "#EF6C00"),
            ("overdue", f"Ληξιπρόθεσμες (>{OVERDUE_DAYS} ημ.)", "#B71C1C"),
        ]
        for i, (key, label, color) in enumerate(cards):
            kpi.addWidget(self._make_card(key, label, color), 0, i)
        root.addLayout(kpi)

        # Filter bar
        fbar = QHBoxLayout()
        fbar.setSpacing(8)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Αναζήτηση πελάτη (όνομα, κωδικός)…")
        self.search_edit.textChanged.connect(self._on_search_changed)
        self.search_edit.setClearButtonEnabled(True)
        fbar.addWidget(self.search_edit, 2)

        fbar.addWidget(QLabel("Ελάχ. ποσό €:"))
        self.min_edit = QLineEdit()
        self.min_edit.setPlaceholderText("0")
        self.min_edit.setFixedWidth(80)
        self.min_edit.textChanged.connect(self._on_min_changed)
        fbar.addWidget(self.min_edit)

        self.overdue_cb = QCheckBox("Μόνο ληξιπρόθεσμες")
        self.overdue_cb.stateChanged.connect(self._on_overdue_toggled)
        fbar.addWidget(self.overdue_cb)

        fbar.addWidget(QLabel("Ταξινόμηση:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Ποσό (φθίνουσα)", "amount")
        self.sort_combo.addItem("Παλαιότητα", "age")
        self.sort_combo.addItem("Όνομα", "name")
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        fbar.addWidget(self.sort_combo)

        fbar.addStretch()
        root.addLayout(fbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Κωδικός", "Πελάτης", "Τηλέφωνο", "Πλάνο",
            "Παλαιότερη οφειλή", "Ανοιχτές", "Οφειλή €",
        ])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._on_open_card)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in (0, 2, 3, 4, 5, 6):
            hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        root.addWidget(self.table, 1)

        # Action buttons
        actions = QHBoxLayout()
        self.pay_btn = QPushButton("Καταχώρηση Πληρωμής")
        self.pay_btn.setStyleSheet("QPushButton{background-color:#4CAF50;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#45a049;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        self.pay_btn.clicked.connect(self._on_record_payment)
        actions.addWidget(self.pay_btn)

        self.card_btn = QPushButton("Άνοιγμα Καρτέλας")
        self.card_btn.setStyleSheet("QPushButton{background-color:#1976D2;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#1565C0;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        self.card_btn.clicked.connect(self._on_open_card)
        actions.addWidget(self.card_btn)

        actions.addStretch()
        self.total_label = QLabel("Σύνολο: 0.00 €")
        self.total_label.setStyleSheet(
            "font-size:16px;font-weight:bold;color:#C62828;")
        actions.addWidget(self.total_label)
        root.addLayout(actions)

    def _make_card(self, key, label, color):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:white;border:1px solid #E0E0E0;"
            f"border-left:5px solid {color};border-radius:8px;}}")
        card.setMinimumHeight(84)
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 10, 16, 10)
        value = QLabel("—")
        value.setStyleSheet(
            f"font-size:24px;font-weight:bold;color:{color};border:none;")
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size:12px;color:#555;border:none;")
        lbl.setWordWrap(True)
        v.addWidget(value)
        v.addWidget(lbl)
        self._kpi_labels[key] = value
        return card

    # ---------- filters ----------
    def _on_search_changed(self, text):
        self.search_text = (text or "").strip().lower()
        self._apply_filters()

    def _on_min_changed(self, text):
        try:
            self.min_amount = float((text or "0").replace(",", "."))
        except ValueError:
            self.min_amount = 0.0
        self._apply_filters()

    def _on_overdue_toggled(self, _state):
        self.only_overdue = self.overdue_cb.isChecked()
        self._apply_filters()

    def _on_sort_changed(self, _idx):
        self.sort_mode = self.sort_combo.currentData() or "amount"
        self._apply_filters()

    # ---------- data load ----------
    def refresh(self):
        """Reload aggregated debts from the database."""
        rows = self._query(
            """
            SELECT f.id                              AS client_id,
                   f.legacy_code                     AS code,
                   f.last_name                       AS last_name,
                   f.first_name                      AS first_name,
                   f.company_name                    AS company_name,
                   f.phone                           AS phone,
                   f.mobile                          AS mobile,
                   f.support_plan                    AS support_plan,
                   f.rustdesk_id                     AS rustdesk_id,
                   COUNT(p.id)                       AS open_count,
                   COALESCE(SUM(p.remaining_amount),0) AS debt,
                   MIN(p.payment_date)               AS oldest_date
            FROM families f
            JOIN payments p ON p.family_id = f.id AND p.remaining_amount > 0
            GROUP BY f.id
            HAVING debt > 0
            """,
            default=[])
        self._rows_cache = rows or []
        self._apply_filters()

    def _apply_filters(self):
        today = date.today()

        def days_old(d):
            if not d:
                return 0
            try:
                if isinstance(d, str):
                    d = date.fromisoformat(d[:10])
                elif hasattr(d, "date"):
                    d = d.date()
                return (today - d).days
            except Exception:
                return 0

        filtered = []
        for r in self._rows_cache:
            debt = float(r.get("debt", 0) or 0)
            if debt <= 0:
                continue
            if debt < self.min_amount:
                continue
            age = days_old(r.get("oldest_date"))
            if self.only_overdue and age < OVERDUE_DAYS:
                continue
            if self.search_text:
                name = f"{r.get('last_name','') or ''} {r.get('first_name','') or ''} {r.get('company_name','') or ''}".lower()
                code = str(r.get("code", "") or "")
                if self.search_text not in name and self.search_text not in code:
                    continue
            r = dict(r)
            r["_age"] = age
            filtered.append(r)

        if self.sort_mode == "amount":
            filtered.sort(key=lambda x: float(x.get("debt", 0) or 0), reverse=True)
        elif self.sort_mode == "age":
            filtered.sort(key=lambda x: x.get("_age", 0), reverse=True)
        else:  # name
            filtered.sort(key=lambda x: (
                (x.get("last_name", "") or "").lower(),
                (x.get("first_name", "") or "").lower()))

        self._populate_table(filtered)
        self._update_kpis(filtered)

    def _populate_table(self, rows):
        self.table.setRowCount(0)
        for r in rows:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)

            debt = float(r.get("debt", 0) or 0)
            age = r.get("_age", 0)
            overdue = age >= OVERDUE_DAYS
            code = str(r.get("code", "") or "")
            name = f"{r.get('last_name','') or ''} {r.get('first_name','') or ''}".strip()
            company = (r.get("company_name") or "").strip()
            if company:
                name = f"{name} ({company})" if name else company
            phone = (r.get("mobile") or r.get("phone") or "").strip() or "—"
            plan = _PLAN_LABELS.get(r.get("support_plan"), r.get("support_plan") or "—")
            oldest = r.get("oldest_date")
            if oldest and hasattr(oldest, "strftime"):
                oldest_str = oldest.strftime("%d/%m/%Y")
            elif oldest:
                oldest_str = str(oldest)[:10]
            else:
                oldest_str = "—"
            age_str = f"{oldest_str}  ({age} ημ.)" if oldest_str != "—" else "—"

            cells = [
                (code, Qt.AlignCenter),
                (name or "—", Qt.AlignVCenter | Qt.AlignLeft),
                (phone, Qt.AlignVCenter | Qt.AlignLeft),
                (plan, Qt.AlignCenter),
                (age_str, Qt.AlignCenter),
                (str(int(r.get("open_count", 0) or 0)), Qt.AlignCenter),
                (f"{debt:.2f} €", Qt.AlignRight | Qt.AlignVCenter),
            ]
            for col, (text, align) in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(align)
                if col == 0:
                    item.setData(Qt.UserRole, r.get("client_id"))
                    item.setData(Qt.UserRole + 1, r.get("rustdesk_id"))
                if col == 6:
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                    item.setForeground(QBrush(QColor("#C62828")))
                # All debt rows share the same red shade (user preference).
                item.setBackground(QBrush(QColor(0xFF, 0xEB, 0xEE)))  # light red
                self.table.setItem(row_idx, col, item)

    def _update_kpis(self, rows):
        total = sum(float(r.get("debt", 0) or 0) for r in rows)
        n_clients = len(rows)
        n_overdue = sum(1 for r in rows if r.get("_age", 0) >= OVERDUE_DAYS)
        self._kpi_labels["total"].setText(f"{total:.2f} €")
        self._kpi_labels["clients"].setText(str(n_clients))
        self._kpi_labels["overdue"].setText(str(n_overdue))
        self.total_label.setText(f"Σύνολο: {total:.2f} €")

    # ---------- selection helpers ----------
    def _selected_client_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _selected_rustdesk_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole + 1) if item else None

    # ---------- actions ----------
    def _on_open_card(self, *args):
        client_id = self._selected_client_id()
        if not client_id:
            QMessageBox.information(self, "Οφειλές",
                                    "Επιλέξτε πρώτα έναν πελάτη.")
            return
        self._open_card_for(client_id)

    def open_client_card(self, client_id):
        """Public entry (e.g. from the dashboard): select the client's row if
        present, then open the client card."""
        if not client_id:
            return
        try:
            for r in range(self.table.rowCount()):
                item = self.table.item(r, 0)
                if item and item.data(Qt.UserRole) == client_id:
                    self.table.selectRow(r)
                    self.table.scrollToItem(item)
                    break
        except Exception:
            pass
        self._open_card_for(client_id)

    def _open_card_for(self, client_id):
        try:
            from ui.widgets.client_card_dialog import ClientCardDialog
            dlg = ClientCardDialog(client_id, self.clients_repo,
                                   self.rustdesk_service, self.tr_manager, self)
            dlg.exec()
            self.refresh()
        except Exception as e:
            logger.error(f"Failed to open client card: {e}", exc_info=True)
            QMessageBox.warning(self, "Σφάλμα",
                                f"Δεν άνοιξε η καρτέλα πελάτη:\n{e}")

    def _on_record_payment(self):
        if not has_permission('payments.create'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα καταχώρησης πληρωμής.")
            return
        client_id = self._selected_client_id()
        if not client_id:
            QMessageBox.information(self, "Οφειλές",
                                    "Επιλέξτε πρώτα έναν πελάτη.")
            return
        # Current outstanding + name straight from the DB (accurate).
        drows = self._query(
            "SELECT COALESCE(SUM(remaining_amount),0) d FROM payments "
            "WHERE family_id=%s AND remaining_amount>0", (client_id,), default=[])
        debt = float(drows[0]['d']) if drows else 0.0
        nrows = self._query(
            "SELECT last_name, first_name FROM families WHERE id=%s",
            (client_id,), default=[])
        if nrows:
            name = f"{nrows[0].get('last_name','') or ''} {nrows[0].get('first_name','') or ''}".strip()
        else:
            name = ""
        if debt <= 0:
            QMessageBox.information(self, "Καταχώρηση Πληρωμής",
                                    f"Ο πελάτης {name} δεν έχει εκκρεμή οφειλή.")
            return
        dlg = DebtPaymentDialog(name, debt, self)
        if dlg.exec():
            amount = dlg.amount()
            if amount <= 0:
                return
            applied = self._apply_debt_payment(client_id, amount)
            remaining = max(0.0, debt - applied)
            QMessageBox.information(
                self, "Καταχώρηση Πληρωμής",
                f"Καταχωρήθηκε πληρωμή {applied:.2f} € για {name}.\n"
                f"Νέο υπόλοιπο: {remaining:.2f} €")
            self.refresh()

    def _apply_debt_payment(self, client_id, amount):
        """Allocate `amount` to the client's open payments, oldest first,
        updating paid_amount / remaining_amount / status. Returns amount applied."""
        open_rows = self._query(
            "SELECT id, paid_amount, remaining_amount FROM payments "
            "WHERE family_id=%s AND remaining_amount>0 "
            "ORDER BY payment_date ASC, id ASC", (client_id,), default=[])
        to_apply = float(amount)
        applied_total = 0.0
        for row in open_rows:
            if to_apply <= 0.005:
                break
            rem = float(row.get('remaining_amount', 0) or 0)
            paid = float(row.get('paid_amount', 0) or 0)
            applied = min(rem, to_apply)
            new_paid = round(paid + applied, 2)
            new_rem = round(rem - applied, 2)
            status = 'PAID' if new_rem <= 0.005 else 'PARTIAL'
            try:
                self.db.execute_update(
                    "UPDATE payments SET paid_amount=%s, remaining_amount=%s, "
                    "status=%s WHERE id=%s",
                    (new_paid, new_rem, status, row.get('id')))
                applied_total += applied
                to_apply -= applied
            except Exception as e:
                logger.error(f"Failed to apply payment to row {row.get('id')}: {e}",
                             exc_info=True)
        return applied_total

    def _on_rustdesk(self):
        rid = self._selected_rustdesk_id()
        if not rid:
            QMessageBox.information(
                self, "RustDesk",
                "Ο επιλεγμένος πελάτης δεν έχει καταχωρημένο RustDesk ID.")
            return
        if not self.rustdesk_service:
            QMessageBox.information(self, "RustDesk",
                                    "Η υπηρεσία RustDesk δεν είναι διαθέσιμη.")
            return
        try:
            self.rustdesk_service.connect_to_client(rid)
        except Exception as e:
            logger.error(f"RustDesk connect failed: {e}", exc_info=True)
            QMessageBox.warning(self, "RustDesk",
                                f"Αποτυχία σύνδεσης RustDesk:\n{e}")

    def _on_export(self):
        if not has_permission('payments.export'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα εξαγωγής οικονομικών δεδομένων.")
            return
        if self.table.rowCount() == 0:
            QMessageBox.information(self, "Εξαγωγή",
                                    "Δεν υπάρχουν οφειλές για εξαγωγή.")
            return
        default_name = f"ofeiles_{date.today().strftime('%Y%m%d')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Αποθήκευση Excel", default_name,
            "Excel (*.xlsx)")
        if not path:
            return
        try:
            self._export_xlsx(path)
            QMessageBox.information(self, "Εξαγωγή",
                                   f"Η εξαγωγή ολοκληρώθηκε:\n{path}")
        except Exception as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            QMessageBox.warning(self, "Σφάλμα",
                                f"Αποτυχία εξαγωγής:\n{e}")

    def _export_xlsx(self, path):
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment

        wb = Workbook()
        ws = wb.active
        ws.title = "Οφειλές"
        headers = ["Κωδικός", "Πελάτης", "Τηλέφωνο", "Πλάνο",
                   "Παλαιότερη οφειλή", "Ανοιχτές", "Οφειλή €"]
        ws.append(headers)
        head_fill = PatternFill("solid", fgColor="C62828")
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = head_fill
            cell.alignment = Alignment(horizontal="center")

        total = 0.0
        for row in range(self.table.rowCount()):
            values = []
            for col in range(7):
                item = self.table.item(row, col)
                values.append(item.text() if item else "")
            # numeric debt for the total (strip " €")
            try:
                total += float(values[6].replace("€", "").replace(",", ".").strip())
            except ValueError:
                pass
            ws.append(values)

        ws.append([])
        ws.append(["", "", "", "", "", "ΣΥΝΟΛΟ", f"{total:.2f} €"])
        last = ws.max_row
        ws.cell(row=last, column=6).font = Font(bold=True)
        ws.cell(row=last, column=7).font = Font(bold=True, color="C62828")

        widths = [10, 34, 16, 16, 22, 10, 14]
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[chr(64 + i)].width = w

        wb.save(path)


class DebtPaymentDialog(QDialog):
    """Small dialog to collect a payment against a client's outstanding debt."""

    def __init__(self, client_name, total_debt, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Καταχώρηση Πληρωμής")
        self.setMinimumWidth(380)
        self.total_debt = float(total_debt or 0)
        self._build(client_name)

    def _build(self, client_name):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        title = QLabel(client_name or "—")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1F3B57;")
        lay.addWidget(title)

        debt_lbl = QLabel(f"Συνολική Οφειλή:  {self.total_debt:.2f} €")
        debt_lbl.setStyleSheet("color:#C62828;font-weight:bold;font-size:14px;")
        lay.addWidget(debt_lbl)

        form = QFormLayout()
        form.setSpacing(8)
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.0, self.total_debt if self.total_debt > 0 else 999999.99)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSuffix(" €")
        self.amount_spin.setValue(self.total_debt)
        self.amount_spin.valueChanged.connect(self._update_remaining)
        form.addRow("Ποσό Πληρωμής:", self.amount_spin)

        self.remaining_lbl = QLabel()
        form.addRow("Νέο Υπόλοιπο:", self.remaining_lbl)
        lay.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Καταχώρηση")
        btns.button(QDialogButtonBox.Cancel).setText("Άκυρο")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        self._update_remaining()

    def _update_remaining(self):
        rem = self.total_debt - float(self.amount_spin.value())
        if rem < 0:
            rem = 0.0
        self.remaining_lbl.setText(f"{rem:.2f} €")
        color = "#2E7D32" if rem <= 0.005 else "#EF6C00"
        self.remaining_lbl.setStyleSheet(f"font-weight:bold;font-size:14px;color:{color};")

    def amount(self):
        return float(self.amount_spin.value())
