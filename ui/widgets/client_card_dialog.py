# -*- coding: utf-8 -*-
"""
Client Card (360° view) dialog for Support CRM.
Consolidates everything about one client: details, prepaid-hours balance,
debts, sessions and payments — read-only, with an Edit button that reuses
the existing ClientForm.
"""
import logging
from services.audit_context import log_audit
from resources.icons import get_icon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QPushButton,
    QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,
    QMessageBox, QComboBox, QDoubleSpinBox, QFormLayout, QDialogButtonBox, QDateEdit,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush
from ui.utils.permission_helper import has_permission

logger = logging.getLogger(__name__)

SESSION_TYPE = {"remote": "Απομακρυσμένη", "phone": "Τηλεφωνική", "onsite": "Επιτόπου"}
SESSION_STATUS = {"completed": "Ολοκληρωμένη", "active": "Ενεργή", "cancelled": "Ακυρωμένη"}
PAY_STATUS = {"PAID": "Εξοφλημένο", "PARTIAL": "Μερική", "UNPAID": "Ανεξόφλητο"}
PLAN = {"hourly": "Ωριαία Χρέωση", "monthly": "Μηνιαία Συνδρομή",
        "yearly": "Ετήσια Συνδρομή", "custom": "Προσαρμοσμένο"}


def fmt_hours(h):
    try:
        tm = int(round(float(h or 0) * 60))
    except (TypeError, ValueError):
        tm = 0
    if tm <= 0:
        return "0 λεπτά"
    hh, mm = divmod(tm, 60)
    wh = "ώρα" if hh == 1 else "ώρες"
    wm = "λεπτό" if mm == 1 else "λεπτά"
    if hh and mm:
        return f"{hh} {wh} {mm} {wm}"
    return f"{hh} {wh}" if hh else f"{mm} {wm}"


def _fmt_dt(v, with_time=True):
    if hasattr(v, "strftime"):
        return v.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")
    return str(v or "")


class ClientCardDialog(QDialog):
    def __init__(self, client_id, clients_repo, rustdesk_service=None,
                 tr_manager=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.clients_repo = clients_repo
        self.db = getattr(clients_repo, "db", None)
        self.rustdesk_service = rustdesk_service
        self.tr_manager = tr_manager
        self.setWindowTitle("Καρτέλα Πελάτη")
        self.resize(920, 680)
        self._build_ui()
        self._load()

    # ---- data ----
    def _q(self, sql, params=None, default=None):
        try:
            rows = self.db.execute_query(sql, params)
            return rows if rows is not None else (default or [])
        except Exception as e:
            logger.error(f"ClientCard query failed: {e}")
            return default if default is not None else []

    # ---- ui ----
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.header = QFrame()
        self.header.setStyleSheet("QFrame{background:#1976D2;}")
        hl = QVBoxLayout(self.header)
        hl.setContentsMargins(20, 14, 20, 14)
        self.name_lbl = QLabel("—")
        self.name_lbl.setStyleSheet("color:white;font-size:22px;font-weight:bold;")
        self.sub_lbl = QLabel("")
        self.sub_lbl.setStyleSheet("color:#E3F2FD;font-size:12px;")
        rd_row = QHBoxLayout()
        self.rd_lbl = QLabel("")
        self.rd_lbl.setStyleSheet("color:#E3F2FD;font-size:12px;")
        rd_row.addWidget(self.rd_lbl)
        rd_row.addStretch()
        hl.addWidget(self.name_lbl)
        hl.addWidget(self.sub_lbl)
        hl.addLayout(rd_row)
        root.addWidget(self.header)

        body = QVBoxLayout()
        body.setContentsMargins(16, 12, 16, 12)
        body.setSpacing(12)
        root.addLayout(body)

        # KPI strip
        self.kpi_row = QHBoxLayout()
        self.kpi_row.setSpacing(10)
        self._kpi = {}
        for key, label, color in [
            ("hours", "Υπόλοιπο Ωρών", "#6A1B9A"),
            ("debt", "Συνολική Οφειλή", "#C62828"),
            ("sessions", "Σύνολο Συνεδριών", "#00838F"),
            ("last", "Τελευταία Συνεδρία", "#455A64"),
        ]:
            card = QFrame()
            card.setStyleSheet(
                f"QFrame{{background:white;border:1px solid #E0E0E0;border-left:4px solid {color};border-radius:6px;}}")
            v = QVBoxLayout(card); v.setContentsMargins(12, 8, 12, 8)
            val = QLabel("—"); val.setStyleSheet(f"font-size:18px;font-weight:bold;color:{color};border:none;")
            lb = QLabel(label); lb.setStyleSheet("font-size:11px;color:#666;border:none;")
            v.addWidget(val); v.addWidget(lb)
            self._kpi[key] = val
            self.kpi_row.addWidget(card)
        body.addLayout(self.kpi_row)

        # Tabs
        self.tabs = QTabWidget()
        body.addWidget(self.tabs, 1)

        self.tab_overview = QWidget(); self.tabs.addTab(self.tab_overview, "Επισκόπηση")
        self.ov_layout = QVBoxLayout(self.tab_overview)

        self.tbl_sessions = self._make_table(
            ["Ημερομηνία", "Τύπος", "Διάρκεια", "Χρέωση", "Κατάσταση"])
        self.tabs.addTab(self._wrap(self.tbl_sessions), "Συνεδρίες")

        self.tbl_payments = self._make_table(
            ["Ημερομηνία", "Περιγραφή", "Σύνολο", "Πληρωμένο", "Υπόλοιπο", "Κατάσταση"])
        self.tabs.addTab(self._wrap(self.tbl_payments), "Πληρωμές & Οφειλές")

        self.tbl_hours = self._make_table(
            ["Συνολικές", "Χρησιμοπ.", "Υπόλοιπο", "Αγορά", "Λήξη", "Κατάσταση"])
        self.tabs.addTab(self._wrap(self.tbl_hours), "Πακέτα / Ώρες")

        # Footer
        footer = QHBoxLayout()
        self.add_pkg_btn = QPushButton(get_icon('add'), "Προσθήκη Πακέτου")
        self.add_pkg_btn.setStyleSheet("QPushButton{background-color:#4CAF50;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#45a049;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        self.add_pkg_btn.clicked.connect(self._add_package)
        footer.addWidget(self.add_pkg_btn)
        footer.addStretch()
        self.edit_btn = QPushButton(get_icon('edit'), "Επεξεργασία")
        self.edit_btn.setStyleSheet("QPushButton{background-color:#F9A825;color:#212121;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#F57F17;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        self.edit_btn.clicked.connect(self._edit)
        close_btn = QPushButton("Κλείσιμο")
        close_btn.setStyleSheet("QPushButton{padding:8px 16px;}")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(self.edit_btn)
        footer.addWidget(close_btn)
        body.addLayout(footer)

    def _make_table(self, headers):
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setStretchLastSection(True)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        return t

    def _wrap(self, table):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(table)
        return w

    def _row_label(self, text):
        lb = QLabel(text); lb.setStyleSheet("font-size:13px;color:#333;")
        lb.setWordWrap(True)
        return lb

    # ---- load ----
    def _load(self):
        c = None
        try:
            c = self.clients_repo.get_client_by_id(self.client_id)
        except Exception as e:
            logger.error(f"load client failed: {e}")
        if not c:
            self.name_lbl.setText("Ο πελάτης δεν βρέθηκε")
            return
        ln = c.get("last_name", "") or ""
        fn = c.get("first_name", "") or ""
        self.name_lbl.setText(f"{ln} {fn}".strip() or "—")
        plan = PLAN.get(c.get("support_plan", ""), c.get("support_plan", "") or "—")
        active = "● Ενεργός" if c.get("is_active", 1) else "● Ανενεργός"
        parts = [f"Κωδικός: {c.get('legacy_code','—')}", f"Πλάνο: {plan}", active]
        if c.get("city"): parts.append(f"Πόλη: {c.get('city')}")
        if c.get("phone"): parts.append(f"Τηλ: {c.get('phone')}")
        if c.get("mobile"): parts.append(f"Κιν: {c.get('mobile')}")
        self.sub_lbl.setText("   ·   ".join(parts))
        rd = (c.get("rustdesk_id") or "").strip()
        if rd:
            self.rd_lbl.setText(f"RustDesk ID: {rd}")
            self.rd_lbl.show()
        else:
            self.rd_lbl.setText("")
            self.rd_lbl.hide()
        self._rd_id = rd

        # KPIs
        hrow = self._q("SELECT COALESCE(SUM(remaining_hours),0) r FROM client_package_hours "
                       "WHERE client_id=%s AND is_active=1 "
                       "AND (expiry_date IS NULL OR expiry_date >= CURDATE())",
                       (self.client_id,), default=[])
        rem_h = float(hrow[0]["r"]) if hrow and hrow[0].get("r") is not None else 0.0
        drow = self._q("SELECT COALESCE(SUM(remaining_amount),0) d FROM payments "
                       "WHERE family_id=%s AND remaining_amount>0", (self.client_id,), default=[])
        debt = float(drow[0]["d"]) if drow and drow[0].get("d") is not None else 0.0
        srow = self._q("SELECT COUNT(*) c, MAX(start_time) last FROM support_sessions "
                       "WHERE client_id=%s", (self.client_id,), default=[])
        scount = int(srow[0]["c"]) if srow and srow[0].get("c") is not None else 0
        slast = srow[0].get("last") if srow else None
        self._kpi["hours"].setText(fmt_hours(rem_h))
        self._kpi["debt"].setText(f"{debt:.2f} €")
        self._kpi["sessions"].setText(str(scount))
        self._kpi["last"].setText(_fmt_dt(slast, with_time=False) if slast else "—")

        # Overview tab
        while self.ov_layout.count():
            it = self.ov_layout.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        self.ov_layout.addWidget(self._row_label(f"<b>Email:</b> {c.get('email','') or '—'}"))
        self.ov_layout.addWidget(self._row_label(f"<b>Διεύθυνση:</b> {c.get('address','') or '—'}, {c.get('city','') or ''} {c.get('postal_code','') or ''}"))
        self.ov_layout.addWidget(self._row_label(f"<b>ΑΦΜ:</b> {c.get('national_id','') or '—'}"))
        self.ov_layout.addWidget(self._row_label(f"<b>Πλάνο υποστήριξης:</b> {plan}"))
        if c.get("hourly_rate"):
            self.ov_layout.addWidget(self._row_label(f"<b>Χρέωση/ώρα:</b> {float(c.get('hourly_rate')):.2f} €"))
        self.ov_layout.addWidget(self._row_label(f"<b>Σημειώσεις:</b> {c.get('notes','') or '—'}"))
        self.ov_layout.addStretch()

        self._load_sessions()
        self._load_payments()
        self._load_hours()

    def _fill(self, table, rows):
        table.setRowCount(0)
        for r in rows:
            i = table.rowCount(); table.insertRow(i)
            for j, val in enumerate(r):
                table.setItem(i, j, QTableWidgetItem(str(val)))

    def _load_sessions(self):
        rows = self._q("SELECT start_time, session_type, duration_minutes, billed_amount, status "
                       "FROM support_sessions WHERE client_id=%s ORDER BY start_time DESC LIMIT 200",
                       (self.client_id,), default=[])
        data = []
        kinds = []  # 'pkg' | 'amount' | 'none' -> gia xromatismo tou keliou xrewsis
        for r in rows:
            dm = int(r.get("duration_minutes", 0) or 0)
            dur = fmt_hours(dm / 60.0) if dm >= 60 else f"{dm} λεπτά"
            status = (r.get("status") or "")
            billed = float(r.get("billed_amount", 0) or 0)
            if status == "cancelled":
                charge, kind = "—", "none"                  # cancelled -> no charge
            elif billed > 0:
                charge, kind = f"{billed:.2f} €", "amount"  # hourly -> amount
            else:
                charge, kind = "Πακέτο", "pkg"  # covered by package/subscription
            kinds.append(kind)
            data.append([_fmt_dt(r.get("start_time")),
                         SESSION_TYPE.get(r.get("session_type"), r.get("session_type") or "—"),
                         dur, charge,
                         SESSION_STATUS.get(r.get("status"), r.get("status") or "—")])
        self._fill(self.tbl_sessions, data)
        # colour the charge cell: green "Paketo" (covered), grey dash (no charge)
        for i, kind in enumerate(kinds):
            it = self.tbl_sessions.item(i, 3)
            if not it:
                continue
            if kind == "pkg":
                it.setForeground(QBrush(QColor("#2E7D32")))
                f = it.font(); f.setBold(True); it.setFont(f)
            elif kind == "none":
                it.setForeground(QBrush(QColor("#9E9E9E")))
        self.tabs.setTabText(1, f"Συνεδρίες ({len(data)})")

    def _load_payments(self):
        rows = self._q("SELECT payment_date, description, total_amount, paid_amount, remaining_amount, status "
                       "FROM payments WHERE family_id=%s ORDER BY payment_date DESC LIMIT 200",
                       (self.client_id,), default=[])
        data = []
        for r in rows:
            data.append([_fmt_dt(r.get("payment_date"), with_time=False),
                         r.get("description", "") or "—",
                         f"{float(r.get('total_amount',0) or 0):.2f} €",
                         f"{float(r.get('paid_amount',0) or 0):.2f} €",
                         f"{float(r.get('remaining_amount',0) or 0):.2f} €",
                         PAY_STATUS.get(r.get("status"), r.get("status") or "—")])
        self._fill(self.tbl_payments, data)
        self.tabs.setTabText(2, f"Πληρωμές & Οφειλές ({len(data)})")

    def _load_hours(self):
        from datetime import date
        today = date.today()
        rows = self._q("SELECT total_hours, used_hours, remaining_hours, purchase_date, "
                       "expiry_date, is_active "
                       "FROM client_package_hours WHERE client_id=%s ORDER BY purchase_date DESC",
                       (self.client_id,), default=[])
        data = []
        inactive_flags = []
        for r in rows:
            exp = r.get("expiry_date")
            is_expired = False
            if exp:
                try:
                    ed = exp.date() if hasattr(exp, "date") else (
                        exp if hasattr(exp, "year") else date.fromisoformat(str(exp)[:10]))
                    is_expired = ed < today
                except Exception:
                    is_expired = False
            if not r.get("is_active", 1):
                status = "Ανενεργό"
                greyed = True
            elif is_expired:
                status = "Έληξε"
                greyed = True
            else:
                status = "Ενεργό"
                greyed = False
            inactive_flags.append(greyed)
            data.append([fmt_hours(r.get("total_hours")), fmt_hours(r.get("used_hours")),
                         fmt_hours(r.get("remaining_hours")),
                         _fmt_dt(r.get("purchase_date"), with_time=False),
                         _fmt_dt(r.get("expiry_date"), with_time=False),
                         status])
        self._fill(self.tbl_hours, data)
        # Mark expired / inactive packages in red so they clearly do not count.
        for i, greyed in enumerate(inactive_flags):
            if not greyed:
                continue
            for j in range(self.tbl_hours.columnCount()):
                it = self.tbl_hours.item(i, j)
                if it:
                    it.setForeground(QBrush(QColor("#C62828")))
            st = self.tbl_hours.item(i, 5)
            if st:
                f = st.font(); f.setBold(True); st.setFont(f)
        self.tabs.setTabText(3, f"Πακέτα / Ώρες ({len(data)})")

    # ---- actions ----
    def _connect_rustdesk(self):
        if not (self.rustdesk_service and getattr(self, "_rd_id", "")):
            return
        try:
            ok = self.rustdesk_service.connect_to_client(self._rd_id)
            if not ok:
                QMessageBox.warning(self, "RustDesk", "Δεν ήταν δυνατή η σύνδεση μέσω RustDesk.")
        except Exception as e:
            logger.error(f"rustdesk connect failed: {e}")
            QMessageBox.warning(self, "RustDesk", "Σφάλμα κατά τη σύνδεση RustDesk.")

    def _add_package(self):
        if not has_permission('clients.edit'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα προσθήκης πακέτου στον πελάτη.")
            return
        pkgs = self._q(
            "SELECT id, name, prepaid_hours, price, duration_months "
            "FROM support_packages WHERE is_active=1 "
            "ORDER BY prepaid_hours IS NULL, prepaid_hours, price", default=[])
        if not pkgs:
            QMessageBox.information(
                self, "Πακέτα",
                "Δεν υπάρχουν διαθέσιμα πακέτα στον κατάλογο.")
            return
        dlg = AddPackageDialog(pkgs, self)
        if dlg.exec():
            d = dlg.result_data()
            if not d:
                return
            try:
                self.db.execute_update(
                    "INSERT INTO client_package_hours "
                    "(client_id, package_id, total_hours, used_hours, "
                    "purchase_date, expiry_date, is_active) "
                    "VALUES (%s,%s,%s,0,%s,%s,1)",
                    (self.client_id, d['package_id'], d['total_hours'],
                     d['purchase_date'], d['expiry_date']))
                # Δημιουργία πληρωμής για το πακέτο + προσφορά έκδοσης παραστατικού
                pay_id = None
                try:
                    prow = self._q("SELECT name, price FROM support_packages WHERE id=%s", (d['package_id'],))
                    pname = (prow[0]['name'] if prow else '') or 'Πακέτο'
                    price = float((prow[0]['price'] if prow else 0) or 0)
                    pdate = d.get('purchase_date')
                    try:
                        yr = pdate.year
                    except Exception:
                        try:
                            yr = int(str(pdate)[:4])
                        except Exception:
                            yr = None
                    if price > 0:
                        pay_id = self.db.execute_update(
                            "INSERT INTO payments (family_id, payment_date, description, "
                            "total_amount, paid_amount, remaining_amount, status, year) "
                            "VALUES (%s,%s,%s,%s,%s,0,'PAID',%s)",
                            (self.client_id, pdate, f"Πακέτο: {pname}", price, price, yr))
                        self.db.commit()
                        log_audit(self.db, 'payments', pay_id, 'INSERT', None,
                                  {'family_id': self.client_id, 'description': f"Πακέτο: {pname}",
                                   'amount': price})
                except Exception as _e:
                    logger.error(f"package payment failed: {_e}", exc_info=True)
                QMessageBox.information(self, "Πακέτα", "Το πακέτο προστέθηκε.")
                self._load()
                if pay_id:
                    try:
                        from ui.widgets.document_type_dialog import issue_document_from_db
                        issue_document_from_db(self, pay_id, self.db,
                                               clients_repo=self.clients_repo,
                                               client_id=self.client_id)
                    except Exception as _e:
                        logger.warning(f"issue document failed: {_e}")
            except Exception as e:
                logger.error(f"add package failed: {e}", exc_info=True)
                QMessageBox.warning(self, "Σφάλμα",
                                    f"Δεν προστέθηκε το πακέτο:\n{e}")

    def _edit(self):
        if not has_permission('clients.edit'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα επεξεργασίας πελάτη.")
            return
        try:
            from ui.widgets.client_form import ClientForm
            dlg = ClientForm(clients_repo=self.clients_repo, tr_manager=self.tr_manager,
                             client_id=self.client_id, parent=self)
            dlg.client_saved.connect(lambda *_: self._load())
            dlg.exec()
        except Exception as e:
            logger.error(f"open edit form failed: {e}")


class AddPackageDialog(QDialog):
    """Quick dialog to assign a support package (prepaid hours) to a client."""

    def __init__(self, packages, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Προσθήκη Πακέτου")
        self.setMinimumWidth(420)
        self.packages = packages
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)

        self.pkg_combo = QComboBox()
        for p in self.packages:
            hrs = float(p.get("prepaid_hours") or 0)
            price = float(p.get("price") or 0)
            htxt = f"{hrs:.0f} ώρες" if hrs else "ωριαία"
            self.pkg_combo.addItem(f"{p['name']}  ({htxt}, {price:.0f}€)", p)
        self.pkg_combo.currentIndexChanged.connect(self._on_pkg)
        form.addRow("Πακέτο:", self.pkg_combo)

        self.hours_spin = QDoubleSpinBox()
        self.hours_spin.setRange(0.0, 9999.0)
        self.hours_spin.setDecimals(2)
        self.hours_spin.setSuffix(" ώρες")
        form.addRow("Προπληρωμένες Ώρες:", self.hours_spin)

        self.purchase_edit = QDateEdit(QDate.currentDate())
        self.purchase_edit.setCalendarPopup(True)
        self.purchase_edit.setDisplayFormat("dd/MM/yyyy")
        self.purchase_edit.dateChanged.connect(self._sync_expiry)
        form.addRow("Ημ/νία Αγοράς:", self.purchase_edit)

        self.expiry_edit = QDateEdit(QDate.currentDate().addYears(1))
        self.expiry_edit.setCalendarPopup(True)
        self.expiry_edit.setDisplayFormat("dd/MM/yyyy")
        form.addRow("Ημ/νία Λήξης:", self.expiry_edit)

        lay.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Προσθήκη")
        btns.button(QDialogButtonBox.Cancel).setText("Άκυρο")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        self._on_pkg()

    def _current_months(self):
        p = self.pkg_combo.currentData()
        try:
            return int(p.get("duration_months") or 0)
        except Exception:
            return 0

    def _on_pkg(self):
        p = self.pkg_combo.currentData()
        if not p:
            return
        self.hours_spin.setValue(float(p.get("prepaid_hours") or 0))
        self._sync_expiry()

    def _sync_expiry(self):
        months = self._current_months()
        base = self.purchase_edit.date()
        self.expiry_edit.setDate(base.addMonths(months) if months else base.addYears(1))

    def result_data(self):
        p = self.pkg_combo.currentData()
        if not p:
            return None
        return {
            "package_id": p["id"],
            "total_hours": float(self.hours_spin.value()),
            "purchase_date": self.purchase_edit.date().toString("yyyy-MM-dd"),
            "expiry_date": self.expiry_edit.date().toString("yyyy-MM-dd"),
        }
