# -*- coding: utf-8 -*-
"""
Χρήστες — admin-only management of employees/technicians.
The 'admin' account can view credentials and create/edit/delete users.
"""

import logging

from ui.utils.ui_helpers import gr_question
from resources.icons import get_icon
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QDialog, QFormLayout, QLineEdit, QComboBox, QCheckBox,
    QDialogButtonBox, QMessageBox, QToolButton, QScrollArea, QGroupBox,
)

logger = logging.getLogger(__name__)


class UsersView(QWidget):
    """Admin-only user management with visible credentials."""

    def __init__(self, db_connection, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self._build()
        self.load()

    def _is_admin(self):
        try:
            from ui.utils import get_auth_service
            auth = get_auth_service()
            u = auth.current_user if auth else None
            return bool(u and u.username == 'admin')
        except Exception:
            return False

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Χρήστες")
        title.setStyleSheet("font-size:20px;font-weight:700;")
        layout.addWidget(title)

        note = QLabel("Τεχνικοί της εταιρείας με τα στοιχεία σύνδεσής τους. "
                      "Ορατό μόνο στον διαχειριστή.")
        note.setStyleSheet("color:#6B7785;font-size:12px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        bar = QHBoxLayout()
        self.new_btn = QPushButton(get_icon('add'), "Νέος χρήστης")
        self.new_btn.clicked.connect(self._on_new)
        self.new_btn.setStyleSheet("QPushButton{background-color:#4CAF50;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#45a049;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        bar.addWidget(self.new_btn)
        self.edit_btn = QPushButton(get_icon('edit'), "Επεξεργασία")
        self.edit_btn.clicked.connect(self._on_edit)
        self.edit_btn.setStyleSheet("QPushButton{background-color:#F9A825;color:#212121;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#F57F17;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        bar.addWidget(self.edit_btn)
        self.delete_btn = QPushButton(get_icon('delete'), "Διαγραφή")
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.setStyleSheet("QPushButton{background-color:#E53935;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#C62828;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        bar.addWidget(self.delete_btn)
        bar.addStretch(1)
        self.refresh_btn = QPushButton("Ανανέωση")
        self.refresh_btn.clicked.connect(self.load)
        bar.addWidget(self.refresh_btn)
        layout.addLayout(bar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Όνομα", "Username", "Ρόλος", "Κωδικός", "Κατάσταση"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._on_edit)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2, 3, 4):
            hh.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        self.blocked_label = QLabel("Δεν έχετε πρόσβαση σε αυτή την οθόνη.")
        self.blocked_label.setStyleSheet("color:#C62828;font-size:14px;")
        self.blocked_label.setVisible(False)
        layout.addWidget(self.blocked_label)

    def _groups(self):
        try:
            return self.db.execute_query(
                "SELECT id, name FROM user_groups WHERE name <> 'Προβολή' ORDER BY id") or []
        except Exception as e:
            logger.error(f"load groups failed: {e}")
            return []

    def load(self):
        if not self._is_admin():
            self.table.setVisible(False)
            for b in (self.new_btn, self.edit_btn, self.delete_btn):
                b.setEnabled(False)
            self.blocked_label.setVisible(True)
            return
        self.table.setVisible(True)
        self.blocked_label.setVisible(False)
        for b in (self.new_btn, self.edit_btn, self.delete_btn):
            b.setEnabled(True)

        try:
            rows = self.db.execute_query(
                "SELECT u.id, u.first_name, u.last_name, u.username, u.plain_password, "
                "u.is_active, u.is_system, u.group_id, g.name AS role "
                "FROM users u LEFT JOIN user_groups g ON u.group_id = g.id "
                "ORDER BY u.is_system DESC, u.username") or []
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
            rows = []

        self.table.setRowCount(0)
        for r in rows:
            name = ("%s %s" % (r.get('first_name', '') or '',
                               r.get('last_name', '') or '')).strip() or "—"
            pwd = "********" if r.get('plain_password') else "—"
            active = "Ενεργός" if str(r.get('is_active')) in ('1', 'True', 'true') else "Ανενεργός"
            role = r.get('role') or "—"
            row = self.table.rowCount()
            self.table.insertRow(row)
            vals = [name, r.get('username') or '', role, pwd, active]
            for col, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                if col in (1, 3):
                    it.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                if col == 0:
                    it.setData(Qt.UserRole, r)  # keep full record on the row
                self.table.setItem(row, col, it)

    def _selected_record(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        it = self.table.item(row, 0)
        return it.data(Qt.UserRole) if it else None

    def _on_new(self):
        dlg = UserEditDialog(self.db, self._groups(), record=None, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.load()

    def _on_edit(self, *_):
        rec = self._selected_record()
        if not rec:
            QMessageBox.information(self, "Χρήστες", "Επιλέξτε χρήστη από τη λίστα.")
            return
        dlg = UserEditDialog(self.db, self._groups(), record=rec, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.load()

    def _on_delete(self):
        rec = self._selected_record()
        if not rec:
            QMessageBox.information(self, "Χρήστες", "Επιλέξτε χρήστη από τη λίστα.")
            return
        if str(rec.get('is_system')) in ('1', 'True', 'true'):
            QMessageBox.warning(self, "Χρήστες", "Ο χρήστης συστήματος δεν διαγράφεται.")
            return
        try:
            _adm = self.db.execute_query(
                "SELECT id FROM user_groups WHERE name='Διαχειριστές'")
            _adm_id = _adm[0]['id'] if _adm else 1
            if rec.get('group_id') == _adm_id:
                _cnt = self.db.execute_query(
                    "SELECT COUNT(*) AS c FROM users WHERE group_id=%s AND is_active=1",
                    (_adm_id,))
                if (_cnt[0]['c'] if _cnt else 0) <= 1:
                    QMessageBox.warning(self, "Δεν επιτρέπεται",
                        "Αυτός είναι ο μοναδικός ενεργός διαχειριστής και δεν διαγράφεται.")
                    return
        except Exception as e:
            logger.error(f"admin guard failed: {e}")
        if gr_question(
                self, "Διαγραφή",
                f"Διαγραφή του χρήστη «{rec.get('username')}»;",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            self.db.execute_update("DELETE FROM users WHERE id=%s AND is_system=0",
                                   (rec.get('id'),))
            self.db.commit()
            try:
                from services.audit_context import log_audit
                log_audit(self.db, 'users', rec.get('id'), 'DELETE',
                          {'username': rec.get('username')}, None)
            except Exception:
                pass
            self.load()
        except Exception as e:
            logger.error(f"delete user failed: {e}")
            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία διαγραφής:\n{e}")


class UserEditDialog(QDialog):
    """Create or edit a user (with visible password)."""

    def __init__(self, db, groups, record=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.groups = groups or []
        self.record = record
        self.is_edit = record is not None
        self.is_system = bool(record and str(record.get('is_system')) in ('1', 'True', 'true'))
        self.setWindowTitle("Επεξεργασία Χρήστη" if self.is_edit else "Νέος Χρήστης")
        self.setMinimumSize(520, 700)
        self.setStyleSheet(self._dialog_qss())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- Header ----
        header = QWidget(self)
        header.setObjectName("dlgHeader")
        h = QVBoxLayout(header)
        h.setContentsMargins(24, 18, 24, 18)
        h.setSpacing(2)
        htitle = QLabel("Επεξεργασία Χρήστη" if self.is_edit else "Νέος Χρήστης")
        htitle.setObjectName("dlgTitle")
        hsub = QLabel("Στοιχεία λογαριασμού και δικαιώματα πρόσβασης")
        hsub.setObjectName("dlgSub")
        h.addWidget(htitle)
        h.addWidget(hsub)
        outer.addWidget(header)

        # ---- Body form ----
        body = QWidget(self)
        body.setObjectName("dlgBody")
        form = QFormLayout(body)
        form.setContentsMargins(24, 20, 24, 8)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.first_input = QLineEdit(record.get('first_name', '') if record else '')
        self.first_input.setPlaceholderText("π.χ. Γιάννης")
        form.addRow("Όνομα:", self.first_input)
        self.last_input = QLineEdit(record.get('last_name', '') if record else '')
        self.last_input.setPlaceholderText("π.χ. Παπαδόπουλος")
        form.addRow("Επώνυμο:", self.last_input)

        self.username_input = QLineEdit(record.get('username', '') if record else '')
        self.username_input.setPlaceholderText("όνομα σύνδεσης")
        if self.is_system:
            self.username_input.setEnabled(False)
            self.username_input.setToolTip("Το username του χρήστη συστήματος δεν αλλάζει.")
        form.addRow("Username *:", self.username_input)

        self.password_input = QLineEdit(record.get('plain_password', '') if record else '')
        self.password_input.setPlaceholderText("Κωδικός πρόσβασης")
        self.password_input.setEchoMode(QLineEdit.Password)
        self._pw_reveal_btn = QToolButton()
        self._pw_reveal_btn.setObjectName("pwReveal")
        self._pw_reveal_btn.setCheckable(True)
        self._pw_reveal_btn.setText("\U0001F441")
        self._pw_reveal_btn.setToolTip("Εμφάνιση/Απόκρυψη κωδικού")
        self._pw_reveal_btn.setCursor(Qt.PointingHandCursor)
        self._pw_reveal_btn.setFocusPolicy(Qt.NoFocus)
        self._pw_reveal_btn.toggled.connect(self._toggle_password_visibility)
        _pw_row = QHBoxLayout()
        _pw_row.setContentsMargins(0, 0, 0, 0)
        _pw_row.setSpacing(6)
        _pw_row.addWidget(self.password_input, 1)
        _pw_row.addWidget(self._pw_reveal_btn)
        _pw_container = QWidget()
        _pw_container.setLayout(_pw_row)
        form.addRow("Κωδικός *:", _pw_container)

        self.role_combo = QComboBox()
        for g in self.groups:
            self.role_combo.addItem(g.get('name', ''), g.get('id'))
        if record and record.get('group_id') is not None:
            idx = self.role_combo.findData(record.get('group_id'))
            if idx >= 0:
                self.role_combo.setCurrentIndex(idx)
        else:
            tidx = self.role_combo.findData(2)  # default new users to Τεχνικοί
            if tidx >= 0:
                self.role_combo.setCurrentIndex(tidx)
        # Fix Greek clipping in the popup (no native popup + explicit item sizes)
        self.role_combo.setMinimumHeight(36)
        self.role_combo.setMaxVisibleItems(10)
        for _i in range(self.role_combo.count()):
            self.role_combo.setItemData(_i, QSize(0, 34), Qt.SizeHintRole)
        form.addRow("Ρόλος:", self.role_combo)

        self.active_check = QCheckBox("Ενεργός λογαριασμός")
        self.active_check.setChecked(
            True if not record else str(record.get('is_active')) in ('1', 'True', 'true'))
        form.addRow("", self.active_check)
        outer.addWidget(body)

        # ---- Permissions checklist (per-user overrides on top of role) ----
        self._admin_group_id = next(
            (g.get('id') for g in self.groups if g.get('name') == 'Διαχειριστές'), 1)
        self._perm_checks = {}
        self._group_baselines = {}
        self._init_permissions_section(outer)

        # ---- Buttons ----
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_btn = btns.button(QDialogButtonBox.Save)
        save_btn.setText("Αποθήκευση")
        save_btn.setObjectName("btnSave")
        save_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn = btns.button(QDialogButtonBox.Cancel)
        cancel_btn.setText("Άκυρο")
        cancel_btn.setObjectName("btnCancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        btn_wrap = QWidget(self)
        bl = QHBoxLayout(btn_wrap)
        bl.setContentsMargins(24, 4, 24, 18)
        bl.addStretch(1)
        bl.addWidget(btns)
        outer.addWidget(btn_wrap)

    CATEGORY_NAMES = {
        'clients': 'Πελάτες', 'families': 'Πελάτες', 'members': 'Μέλη',
        'sessions': 'Συνεδρίες', 'packages': 'Πακέτα',
        'support': 'Απομακρυσμένη Υποστήριξη', 'payments': 'Πληρωμές / Παραστατικά',
        'subscriptions': 'Συνδρομές', 'reports': 'Αναφορές', 'settings': 'Ρυθμίσεις',
        'users': 'Χρήστες & Ομάδες', 'import': 'Εισαγωγή', 'backup': 'Αντίγραφα Ασφαλείας',
    }

    def _active_admin_count(self):
        try:
            r = self.db.execute_query(
                "SELECT COUNT(*) AS c FROM users WHERE group_id=%s AND is_active=1",
                (self._admin_group_id,))
            return r[0]['c'] if r else 0
        except Exception as e:
            logger.error(f"admin count failed: {e}")
            return 0

    def _load_perm_data(self):
        self._perms_by_cat = {}
        try:
            rows = self.db.execute_query(
                "SELECT id, code, name, category FROM permissions ORDER BY category, id") or []
        except Exception as e:
            logger.error(f"load permissions failed: {e}"); rows = []
        for r in rows:
            self._perms_by_cat.setdefault(r['category'], []).append(r)
        try:
            gp = self.db.execute_query(
                "SELECT group_id, permission_id FROM group_permissions") or []
        except Exception as e:
            logger.error(f"load group_permissions failed: {e}"); gp = []
        for r in gp:
            self._group_baselines.setdefault(r['group_id'], set()).add(r['permission_id'])
        self._user_grants, self._user_denies = set(), set()
        if self.is_edit and self.record.get('id'):
            try:
                ov = self.db.execute_query(
                    "SELECT permission_id, effect FROM user_permissions WHERE user_id=%s",
                    (self.record.get('id'),)) or []
                for r in ov:
                    (self._user_grants if r['effect'] == 'grant'
                     else self._user_denies).add(r['permission_id'])
            except Exception as e:
                logger.error(f"load user_permissions failed: {e}")

    def _init_permissions_section(self, outer):
        wrap = QWidget(self)
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(24, 4, 24, 4); wl.setSpacing(6)
        lbl = QLabel("Δικαιώματα πρόσβασης:")
        lbl.setStyleSheet("font-weight:700; color:#37474F;")
        wl.addWidget(lbl)
        self.perm_hint = QLabel(""); self.perm_hint.setWordWrap(True)
        self.perm_hint.setStyleSheet("color:#78909C; font-weight:400; font-size:12px;")
        wl.addWidget(self.perm_hint)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setMinimumHeight(230)
        cont = QWidget(); cl = QVBoxLayout(cont); cl.setSpacing(8)
        self._load_perm_data()
        for category, perms in self._perms_by_cat.items():
            box = QGroupBox(self.CATEGORY_NAMES.get(category, category))
            bl = QVBoxLayout(box)
            for perm in perms:
                cb = QCheckBox(perm['name']); cb.setToolTip(perm.get('code', ''))
                self._perm_checks[perm['id']] = cb
                bl.addWidget(cb)
            cl.addWidget(box)
        cl.addStretch(1)
        scroll.setWidget(cont)
        wl.addWidget(scroll)
        outer.addWidget(wrap)
        self._sync_perms_to_role(initial=True)
        self.role_combo.currentIndexChanged.connect(lambda *_: self._sync_perms_to_role())

    def _sync_perms_to_role(self, initial=False):
        gid = self.role_combo.currentData()
        if gid == self._admin_group_id:
            for cb in self._perm_checks.values():
                cb.setChecked(True); cb.setEnabled(False)
            self.perm_hint.setText("Ο ρόλος «Διαχειριστές» έχει πάντα πλήρη πρόσβαση σε όλο το σύστημα.")
            return
        baseline = self._group_baselines.get(gid, set())
        for pid, cb in self._perm_checks.items():
            cb.setEnabled(True); cb.setChecked(pid in baseline)
        if initial and self.is_edit:
            for pid, cb in self._perm_checks.items():
                if pid in self._user_grants: cb.setChecked(True)
                elif pid in self._user_denies: cb.setChecked(False)
            self.perm_hint.setText("Τρέχοντα δικαιώματα του χρήστη (ρόλος + προσαρμογές).")
        else:
            self.perm_hint.setText("Προεπιλογή του ρόλου — τσεκάρετε/ξετσεκάρετε για προσαρμογή ανά χρήστη.")

    def _persist_overrides(self, user_id):
        if not user_id:
            return
        gid = self.role_combo.currentData()
        try:
            self.db.execute_update("DELETE FROM user_permissions WHERE user_id=%s", (user_id,))
            if gid != self._admin_group_id:
                baseline = self._group_baselines.get(gid, set())
                for pid, cb in self._perm_checks.items():
                    checked, in_base = cb.isChecked(), pid in baseline
                    if checked and not in_base:
                        self.db.execute_update(
                            "INSERT INTO user_permissions (user_id, permission_id, effect) "
                            "VALUES (%s,%s,'grant')", (user_id, pid))
                    elif not checked and in_base:
                        self.db.execute_update(
                            "INSERT INTO user_permissions (user_id, permission_id, effect) "
                            "VALUES (%s,%s,'deny')", (user_id, pid))
            self.db.commit()
        except Exception as e:
            logger.error(f"persist overrides failed: {e}")

    @staticmethod
    def _dialog_qss():
        return """
        QDialog { background: #FFFFFF; }
        #dlgHeader {
            background: #2196F3;
            border-top-left-radius: 4px; border-top-right-radius: 4px;
        }
        #dlgTitle { color: #FFFFFF; font-size: 17px; font-weight: 700; }
        #dlgSub   { color: rgba(255,255,255,0.85); font-size: 12px; }
        #dlgBody QLabel { color: #37474F; font-size: 13px; font-weight: 600; }
        QLineEdit, QComboBox {
            background: #FFFFFF;
            border: 1px solid #CFD8DC;
            border-radius: 6px;
            padding: 7px 10px;
            font-size: 13px;
            min-height: 20px;
            color: #212121;
        }
        QLineEdit:focus, QComboBox:focus { border: 1px solid #2196F3; }
        QLineEdit:disabled { background: #ECEFF1; color: #90A4AE; }
        QComboBox { combobox-popup: 0; }
        QComboBox::drop-down { border: none; width: 26px; }
        QComboBox QAbstractItemView {
            border: 1px solid #CFD8DC;
            background: #FFFFFF;
            selection-background-color: #E3F2FD;
            selection-color: #0D47A1;
            outline: 0;
        }
        QComboBox QAbstractItemView::item { min-height: 34px; padding: 6px 10px; }
        QCheckBox { color: #37474F; font-size: 13px; font-weight: 600; spacing: 8px; }
        QCheckBox::indicator { width: 18px; height: 18px; }
        QToolButton#pwReveal {
            border: 1px solid #CFD8DC; border-radius: 6px;
            padding: 6px 9px; font-size: 15px; background: #FFFFFF;
        }
        QToolButton#pwReveal:hover { background: #ECEFF1; }
        QToolButton#pwReveal:checked { background: #E3F2FD; border-color: #2196F3; }
        #btnSave {
            background: #2196F3; color: #FFFFFF; border: none;
            border-radius: 6px; padding: 8px 22px; font-size: 13px; font-weight: 700;
        }
        #btnSave:hover { background: #1976D2; }
        #btnCancel {
            background: #ECEFF1; color: #455A64; border: none;
            border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 600;
        }
        #btnCancel:hover { background: #CFD8DC; }
        """

    def _toggle_password_visibility(self, checked):
        self.password_input.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password)
        self._pw_reveal_btn.setText("\U0001F648" if checked else "\U0001F441")

    def _save(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if not username:
            QMessageBox.warning(self, "Username", "Το username είναι υποχρεωτικό.")
            return
        if not password:
            QMessageBox.warning(self, "Κωδικός", "Ο κωδικός είναι υποχρεωτικός.")
            return
        group_id = self.role_combo.currentData()
        is_active = 1 if self.active_check.isChecked() else 0

        # Guard: never leave the system without an active administrator.
        if self.is_edit and self.record.get('group_id') == self._admin_group_id:
            losing_admin = (group_id != self._admin_group_id) or (is_active == 0)
            if losing_admin and self._active_admin_count() <= 1:
                QMessageBox.warning(self, "Δεν επιτρέπεται",
                    "Αυτός είναι ο μοναδικός ενεργός διαχειριστής και δεν μπορεί "
                    "να υποβαθμιστεί ή να απενεργοποιηθεί.")
                return
        first = self.first_input.text().strip()
        last = self.last_input.text().strip()

        try:
            import bcrypt
            pw_hash = bcrypt.hashpw(password.encode('utf-8'),
                                    bcrypt.gensalt(rounds=12)).decode('utf-8')
        except Exception as e:
            QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία κρυπτογράφησης κωδικού:\n{e}")
            return

        try:
            if self.is_edit:
                uid = self.record.get('id')
                if self.is_system:
                    # keep the system username unchanged
                    self.db.execute_update(
                        "UPDATE users SET first_name=%s, last_name=%s, group_id=%s, "
                        "is_active=%s, password_hash=%s, plain_password=%s WHERE id=%s",
                        (first, last, group_id, is_active, pw_hash, password, uid))
                else:
                    self.db.execute_update(
                        "UPDATE users SET username=%s, first_name=%s, last_name=%s, "
                        "group_id=%s, is_active=%s, password_hash=%s, plain_password=%s "
                        "WHERE id=%s",
                        (username, first, last, group_id, is_active, pw_hash, password, uid))
                self.db.commit()
                op, rid = 'UPDATE', uid
            else:
                rid = self.db.execute_update(
                    "INSERT INTO users (username, password_hash, plain_password, email, "
                    "first_name, last_name, group_id, is_active, is_system) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0)",
                    (username, pw_hash, password, f"{username}@example.gr",
                     first, last, group_id, is_active))
                self.db.commit()
                op = 'INSERT'
            try:
                from services.audit_context import log_audit
                log_audit(self.db, 'users', rid, op, None,
                          {'username': username, 'group_id': group_id, 'is_active': is_active})
            except Exception:
                pass
            self._persist_overrides(rid)
            self.accept()
        except Exception as e:
            msg = str(e)
            if '1062' in msg or 'Duplicate' in msg:
                QMessageBox.warning(self, "Username",
                                    "Υπάρχει ήδη χρήστης με αυτό το username.")
            else:
                logger.error(f"save user failed: {e}")
                QMessageBox.critical(self, "Σφάλμα", f"Αποτυχία αποθήκευσης:\n{e}")
