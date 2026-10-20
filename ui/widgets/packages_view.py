# -*- coding: utf-8 -*-
"""
Packages view for Support CRM.
Standalone management screen for the support-package catalog, shown as its
own sidebar entry. Reuses PackageFormDialog for create/edit.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QLabel, QMessageBox, QHeaderView, QDialog, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor

from resources.icons import get_icon
from ui.utils.ui_helpers import fmt_hours_min, gr_question
from ui.utils.permission_helper import has_permission

logger = logging.getLogger(__name__)

TYPE_DISPLAY = {
    'hourly': 'Ωριαία',
    'monthly': 'Μηνιαία',
    'yearly': 'Ετήσια',
    'custom': 'Πακέτο ωρών',
}


class PackagesView(QWidget):
    """Standalone view for managing support packages."""

    def __init__(self, db_connection, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self._init_ui()
        self.refresh()
        logger.debug("PackagesView initialized")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # Header
        title = QLabel("Πακέτα Υποστήριξης")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1565C0;")
        layout.addWidget(title)

        info = QLabel(
            "Ο κατάλογος των πακέτων που προσφέρετε στους πελάτες. Τα πακέτα με "
            "προπληρωμένες ώρες αφαιρούνται αυτόματα από τις συνεδρίες."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666;")
        layout.addWidget(info)

        # Table
        self.table = QTableView()
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.model = QStandardItemModel()
        self.table.setModel(self.model)
        self._setup_columns()
        layout.addWidget(self.table, stretch=1)

        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(self._on_edit)

        # Buttons
        btns = QHBoxLayout()
        btns.setSpacing(10)

        self.new_btn = QPushButton(get_icon('add'), "Νέο Πακέτο")
        self.new_btn.clicked.connect(self._on_new)
        self.new_btn.setEnabled(has_permission('packages.manage'))
        self.new_btn.setStyleSheet("QPushButton{background-color:#4CAF50;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#45a049;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        btns.addWidget(self.new_btn)

        self.edit_btn = QPushButton(get_icon('edit'), "Επεξεργασία")
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._on_edit)
        self.edit_btn.setStyleSheet("QPushButton{background-color:#F9A825;color:#212121;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#F57F17;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        btns.addWidget(self.edit_btn)

        self.delete_btn = QPushButton(get_icon('delete'), "Διαγραφή")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.setStyleSheet("QPushButton{background-color:#E53935;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#C62828;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        btns.addWidget(self.delete_btn)

        btns.addStretch()

        self.refresh_btn = QPushButton(get_icon('refresh'), "Ανανέωση")
        self.refresh_btn.clicked.connect(self.refresh)
        btns.addWidget(self.refresh_btn)

        layout.addLayout(btns)

    def _setup_columns(self):
        headers = ["Όνομα Πακέτου", "Τύπος", "Τιμή", "Διάρκεια",
                   "Προπληρωμένες Ώρες", "Τιμή/ώρα", "Έκπτωση", "Οικονομία",
                   "Ενεργοί Πελάτες", "Κατάσταση"]
        self.model.setHorizontalHeaderLabels(headers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        widths = [190, 110, 90, 100, 150, 95, 95, 110, 130, 90]
        for i, w in enumerate(widths):
            header.resizeSection(i, w)
        header.setStretchLastSection(True)

    # ---- live refresh ----
    def showEvent(self, event):
        """Reload packages every time the screen is shown (live after any change)."""
        super().showEvent(event)
        try:
            self.refresh()
        except Exception as e:
            logger.warning(f"Packages auto-refresh on show failed: {e}")

    # ---- data ----
    def refresh(self):
        try:
            packages = self.db.execute_query(
                "SELECT id, name, package_type, description, price, "
                "duration_months, prepaid_hours, is_active "
                "FROM support_packages "
                "ORDER BY is_active DESC, prepaid_hours IS NULL, prepaid_hours, price"
            )
        except Exception as e:
            logger.error(f"Error loading packages: {e}")
            QMessageBox.critical(self, "Σφάλμα", f"Σφάλμα φόρτωσης πακέτων:\n{e}")
            return

        # active client counts per package
        counts = {}
        try:
            rows = self.db.execute_query(
                "SELECT package_id, COUNT(DISTINCT client_id) c "
                "FROM client_package_hours WHERE remaining_hours > 0 "
                "GROUP BY package_id"
            )
            counts = {r['package_id']: int(r['c']) for r in rows}
        except Exception as e:
            logger.warning(f"Could not load package client counts: {e}")

        self._populate(packages, counts)

    def _populate(self, packages, counts):
        self.model.removeRows(0, self.model.rowCount())
        # Base hourly rate = price of the hourly package (fallback 40)
        base_rate = 0.0
        for p in packages:
            ph_p = p.get('prepaid_hours')
            has_prepaid = bool(ph_p) and float(ph_p) > 0
            # Reference = the genuine hourly package (pay-per-use, no prepaid hours)
            if p.get('package_type') == 'hourly' and not has_prepaid:
                try:
                    base_rate = float(p.get('price', 0) or 0)
                except (TypeError, ValueError):
                    base_rate = 0.0
                break
        if base_rate <= 0:
            base_rate = 40.0

        def _fmt_disc(d):
            t = f"{d:.1f}"
            if t.endswith(".0"):
                t = t[:-2]
            return "-" + t.replace(".", ",") + "%"

        for pkg in packages:
            active = pkg.get('is_active', 1)

            name_item = QStandardItem(pkg.get('name', ''))
            name_item.setData(pkg.get('id'), Qt.UserRole)

            ptype = pkg.get('package_type', 'hourly')
            type_item = QStandardItem(TYPE_DISPLAY.get(ptype, ptype))

            price_item = QStandardItem(f"{float(pkg.get('price', 0)):.2f} €")

            dur = pkg.get('duration_months')
            if dur:
                dur_text = "1 μήνας" if dur == 1 else f"{dur} μήνες"
            else:
                dur_text = "—"
            dur_item = QStandardItem(dur_text)

            ph = pkg.get('prepaid_hours')
            hours_item = QStandardItem(
                fmt_hours_min(ph) if (ph and float(ph) > 0) else "—"
            )

            # --- computed value columns (τι κερδίζει ο πελάτης) ---
            try:
                price_val = float(pkg.get('price', 0) or 0)
            except (TypeError, ValueError):
                price_val = 0.0
            hours_val = float(ph) if (ph and float(ph) > 0) else None
            is_hourly = (ptype == 'hourly')

            if is_hourly:
                perhour_item = QStandardItem(f"{price_val:.2f} €")
                disc_item = QStandardItem("—")
                save_item = QStandardItem("—")
            elif hours_val and base_rate > 0:
                per_hour = price_val / hours_val
                disc = (base_rate - per_hour) / base_rate * 100.0
                save = base_rate * hours_val - price_val
                perhour_item = QStandardItem(f"{per_hour:.2f} €")
                disc_item = QStandardItem(_fmt_disc(disc) if disc > 0.05 else "—")
                save_item = QStandardItem(f"{save:.0f} €" if abs(save) >= 1 else "—")
                if disc > 0.05:
                    green = QColor("#2E7D32")
                    disc_item.setForeground(green)
                    save_item.setForeground(green)
            else:
                perhour_item = QStandardItem("—")
                disc_item = QStandardItem("—")
                save_item = QStandardItem("—")

            n = counts.get(pkg.get('id'), 0)
            count_item = QStandardItem(str(n) if n else "—")

            status_item = QStandardItem("Ενεργό" if active else "Ανενεργό")
            status_item.setForeground(QColor("#2E7D32") if active else QColor("#9E9E9E"))

            row = [name_item, type_item, price_item, dur_item, hours_item,
                   perhour_item, disc_item, save_item, count_item, status_item]
            if not active:
                for it in row:
                    f = it.font()
                    f.setItalic(True)
                    it.setFont(f)
            self.model.appendRow(row)

    # ---- selection ----
    def _on_selection_changed(self):
        has = self.table.selectionModel().hasSelection()
        can_manage = has_permission('packages.manage')
        self.edit_btn.setEnabled(has and can_manage)
        self.delete_btn.setEnabled(has and can_manage)

    def _selected_id(self) -> Optional[int]:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        return self.model.item(sel[0].row(), 0).data(Qt.UserRole)

    # ---- actions ----
    def _on_new(self):
        if not has_permission('packages.manage'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα διαχείρισης πακέτων.")
            return
        from ui.dialogs.support_packages_dialog import PackageFormDialog
        dlg = PackageFormDialog(self.db, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_edit(self):
        if not has_permission('packages.manage'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα διαχείρισης πακέτων.")
            return
        pkg_id = self._selected_id()
        if not pkg_id:
            return
        from ui.dialogs.support_packages_dialog import PackageFormDialog
        dlg = PackageFormDialog(self.db, package_id=pkg_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh()

    def _on_delete(self):
        if not has_permission('packages.manage'):
            QMessageBox.warning(self, "Πρόσβαση Απορρίφθηκε",
                "Δεν έχετε δικαίωμα διαχείρισης πακέτων.")
            return
        pkg_id = self._selected_id()
        if not pkg_id:
            return
        reply = gr_question(
            self, "Επιβεβαίωση Διαγραφής",
            "Είστε σίγουροι ότι θέλετε να διαγράψετε αυτό το πακέτο;\n\n"
            "Σημείωση: Οι υπάρχουσες πληρωμές και οι προπληρωμένες ώρες πελατών "
            "δεν θα επηρεαστούν."
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.db.execute_update("DELETE FROM support_packages WHERE id = %s", (pkg_id,))
            self.db.commit()
            self.refresh()
        except Exception as e:
            logger.error(f"Error deleting package: {e}")
            QMessageBox.critical(
                self, "Σφάλμα",
                f"Δεν ήταν δυνατή η διαγραφή του πακέτου.\n\n"
                f"Πιθανόν χρησιμοποιείται από πελάτες.\n\n{e}"
            )
