# -*- coding: utf-8 -*-
"""
Dashboard View for Support CRM.
Home screen with KPI cards, a 6-month revenue chart and alert panels.
Reads live data from the database via db_connection.execute_query().
"""

import logging
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QPushButton, QToolTip,
    QDialog, QFormLayout, QGroupBox, QTextEdit, QDialogButtonBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QCursor

logger = logging.getLogger(__name__)

def _fmt_hours_min(h):
    """Format decimal hours as Greek hours+minutes, e.g. 0.7 -> '42 λεπτά', 9.3 -> '9 ώρες 18 λεπτά'."""
    try:
        total_min = int(round(float(h) * 60))
    except (TypeError, ValueError):
        total_min = 0
    hh, mm = divmod(total_min, 60)
    wname = "ώρα" if hh == 1 else "ώρες"
    if hh and mm:
        return f"{hh} {wname} {mm} λεπτά"
    if hh:
        return f"{hh} {wname}"
    return f"{mm} λεπτά"


try:
    from PySide6.QtCharts import (
        QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis,
    )
    from PySide6.QtGui import QPainter
    HAS_CHARTS = True
except Exception as _e:  # pragma: no cover
    HAS_CHARTS = False
    logger.warning(f"QtCharts not available, chart will be hidden: {_e}")

_GR_MONTHS = ["", "Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαϊ", "Ιουν",
              "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ"]

SESSION_TYPE = {"remote": "Απομακρυσμένη", "phone": "Τηλεφωνική",
                "onsite": "Επιτόπου", "email": "Email"}
SESSION_STATUS = {"completed": "Ολοκληρωμένη", "active": "Ενεργή",
                  "cancelled": "Ακυρωμένη"}
_STATUS_COLOR = {"active": "#2E7D32", "completed": "#1976D2",
                 "cancelled": "#90A4AE"}


class DashboardView(QWidget):
    """Main dashboard / home view."""

    # Emitted when a client in the alerts panel is clicked: (client_id)
    open_client_in_debts = Signal(int)
    # Emitted when the "expiring packages" section is clicked
    open_expirations = Signal()

    def __init__(self, db_connection, tr_manager=None, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.tr_manager = tr_manager
        self._kpi_labels = {}
        self._build_ui()
        self.refresh()

    # ---------- data helpers ----------
    def _query(self, sql, params=None, default=None):
        try:
            rows = self.db.execute_query(sql, params)
            return rows if rows is not None else (default or [])
        except Exception as e:
            logger.error(f"Dashboard query failed: {e}")
            return default if default is not None else []

    def _scalar(self, sql, params=None, default=0):
        rows = self._query(sql, params, default=[])
        if rows:
            row = rows[0]
            if isinstance(row, dict):
                for v in row.values():
                    return v if v is not None else default
            else:
                return row[0]
        return default

    # ---------- UI ----------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        self.layout_main = QVBoxLayout(container)
        self.layout_main.setContentsMargins(24, 20, 24, 20)
        self.layout_main.setSpacing(18)

        # Header row
        header = QHBoxLayout()
        title = QLabel("Πίνακας Ελέγχου")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1976D2;")
        header.addWidget(title)
        header.addStretch()
        self.refresh_btn = QPushButton("Ανανέωση")
        self.refresh_btn.setStyleSheet("QPushButton{background-color:#1976D2;color:white;font-weight:bold;padding:8px 16px;border:none;border-radius:4px;}QPushButton:hover{background-color:#1565C0;}QPushButton:disabled{background-color:#cccccc;color:#8a8a8a;}")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)
        self.layout_main.addLayout(header)

        # KPI cards grid
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(14)
        cards = [
            ("clients", "Ενεργοί Πελάτες", "#1976D2"),
            ("sessions_total", "Σύνολο Συνεδριών", "#00838F"),
            ("hours_total", "Συνολικές Ώρες Υποστήριξης", "#6A1B9A"),
            ("revenue_total", "Σύνολο Εισπράξεων", "#2E7D32"),
            ("debt_total", "Συνολικές Οφειλές", "#C62828"),
            ("sessions_active", "Ενεργές Συνεδρίες", "#EF6C00"),
        ]
        for i, (key, label, color) in enumerate(cards):
            card = self._make_card(key, label, color)
            self.kpi_grid.addWidget(card, i // 3, i % 3)
        self.layout_main.addLayout(self.kpi_grid)

        # Middle row: chart + alerts
        mid = QHBoxLayout()
        mid.setSpacing(16)

        chart_box = QFrame()
        chart_box.setStyleSheet(
            "QFrame{background:white;border:1px solid #E0E0E0;border-radius:8px;}"
        )
        chart_layout = QVBoxLayout(chart_box)
        ct = QLabel("Εισπράξεις & Οφειλές (τελευταίοι 6 μήνες)")
        ct.setStyleSheet("font-weight:bold;font-size:14px;border:none;")
        chart_layout.addWidget(ct)
        self.chart_container = QVBoxLayout()
        chart_layout.addLayout(self.chart_container)
        chart_box.setMinimumHeight(300)
        chart_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        mid.addWidget(chart_box, 2)

        self.alerts_box = QFrame()
        self.alerts_box.setStyleSheet(
            "QFrame{background:white;border:1px solid #E0E0E0;border-radius:8px;}"
        )
        self.alerts_layout = QVBoxLayout(self.alerts_box)
        self.alerts_box.setMinimumWidth(340)
        mid.addWidget(self.alerts_box, 1)

        self.layout_main.addLayout(mid)

        # Recent sessions
        self.recent_box = QFrame()
        self.recent_box.setStyleSheet(
            "QFrame{background:white;border:1px solid #E0E0E0;border-radius:8px;}"
        )
        self.recent_layout = QVBoxLayout(self.recent_box)
        self.layout_main.addWidget(self.recent_box)

        self.layout_main.addStretch()

    def _make_card(self, key, label, color):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:white;border:1px solid #E0E0E0;border-left:5px solid {color};"
            f"border-radius:8px;}}"
        )
        card.setMinimumHeight(90)
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 12, 16, 12)
        value = QLabel("—")
        value.setStyleSheet(f"font-size:26px;font-weight:bold;color:{color};border:none;")
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size:12px;color:#555;border:none;")
        lbl.setWordWrap(True)
        v.addWidget(value)
        v.addWidget(lbl)
        self._kpi_labels[key] = value
        return card

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            else:
                child = item.layout()
                if child is not None:
                    self._clear_layout(child)

    # ---------- refresh ----------
    def refresh(self):
        try:
            self._load_kpis()
            self._load_chart()
            self._load_alerts()
            self._load_recent()
        except Exception as e:
            logger.error(f"Dashboard refresh error: {e}", exc_info=True)

    def _load_kpis(self):
        # All-time totals so the dashboard reconciles with the other screens
        # (Οφειλές, Πληρωμές, Client Card financials).
        clients = self._scalar(
            "SELECT COUNT(*) n FROM families WHERE is_active=1")
        s_active = self._scalar(
            "SELECT COUNT(*) n FROM support_sessions WHERE status='active'")
        s_total = self._scalar(
            "SELECT COUNT(*) n FROM support_sessions")
        mins = self._scalar(
            "SELECT COALESCE(SUM(duration_minutes),0) m FROM support_sessions "
            "WHERE status='completed'")
        revenue = self._scalar(
            "SELECT COALESCE(SUM(paid_amount),0) s FROM payments")
        debt = self._scalar(
            "SELECT COALESCE(SUM(remaining_amount),0) s FROM payments WHERE remaining_amount>0")

        try:
            hours = float(mins or 0) / 60.0
        except Exception:
            hours = 0.0

        self._kpi_labels["clients"].setText(str(int(clients or 0)))
        self._kpi_labels["sessions_active"].setText(str(int(s_active or 0)))
        self._kpi_labels["sessions_total"].setText(str(int(s_total or 0)))
        self._kpi_labels["hours_total"].setText(_fmt_hours_min(hours))
        self._kpi_labels["revenue_total"].setText(f"{float(revenue or 0):.2f} €")
        self._kpi_labels["debt_total"].setText(f"{float(debt or 0):.2f} €")

    def _last_6_months(self):
        today = date.today()
        y, m = today.year, today.month
        months = []
        for _ in range(6):
            months.append((y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        months.reverse()
        return months

    def _load_chart(self):
        self._clear_layout(self.chart_container)
        months = self._last_6_months()
        start = date(months[0][0], months[0][1], 1)
        start_s = start.strftime('%Y-%m-%d')

        def monthly(col):
            rows = self._query(
                f"SELECT YEAR(payment_date) y, MONTH(payment_date) m, "
                f"COALESCE(SUM({col}),0) s FROM payments "
                f"WHERE payment_date >= %s GROUP BY y, m",
                (start_s,), default=[])
            b = {}
            for r in rows:
                try:
                    b[(int(r['y']), int(r['m']))] = float(r['s'] or 0)
                except Exception:
                    pass
            return [b.get(ym, 0.0) for ym in months]

        paid_vals = monthly("paid_amount")
        debt_vals = monthly("remaining_amount")
        labels = [_GR_MONTHS[ym[1]] for ym in months]

        if not HAS_CHARTS:
            txt = "\n".join(
                f"{l}:  Εισπράξεις {p:.0f}€  ·  Οφειλές {d:.0f}€"
                for l, p, d in zip(labels, paid_vals, debt_vals))
            fallback = QLabel(txt or "Χωρίς δεδομένα")
            fallback.setStyleSheet("border:none;color:#555;")
            fallback.setWordWrap(True)
            self.chart_container.addWidget(fallback)
            return

        paid_set = QBarSet("Εισπράξεις")
        paid_set.append(paid_vals)
        paid_set.setColor(QColor("#2E7D32"))
        debt_set = QBarSet("Οφειλές")
        debt_set.append(debt_vals)
        debt_set.setColor(QColor("#C62828"))

        series = QBarSeries()
        series.append(paid_set)
        series.append(debt_set)
        series.setLabelsVisible(False)
        series.hovered.connect(self._on_bar_hovered)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setBackgroundVisible(False)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        allv = paid_vals + debt_vals
        top = max(allv) if allv and max(allv) > 0 else 100
        axis_y.setRange(0, top)
        axis_y.setTickCount(6)
        axis_y.setLabelFormat("%d")
        axis_y.applyNiceNumbers()
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(260)
        view.setStyleSheet("border:none;")
        self.chart_container.addWidget(view)

    def _on_bar_hovered(self, status, index, barset):
        """Show a tooltip with the exact € amount of the hovered bar."""
        try:
            if status and barset is not None and 0 <= index < barset.count():
                name = barset.label() or ""
                val = float(barset.at(index))
                QToolTip.showText(QCursor.pos(), f"{name}: {val:.2f} €")
            else:
                QToolTip.hideText()
        except Exception:
            pass

    def _section_title(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight:bold;font-size:14px;border:none;")
        return lbl

    def _load_alerts(self):
        self._clear_layout(self.alerts_layout)
        self.alerts_layout.addWidget(self._section_title("⚠️  Οφειλές Πελατών"))
        hint = QLabel("Κάντε κλικ σε πελάτη για άνοιγμα στην οθόνη Οφειλών")
        hint.setStyleSheet("border:none;color:#9AA0A6;font-size:11px;margin:0 0 6px 2px;")
        hint.setWordWrap(True)
        self.alerts_layout.addWidget(hint)

        overdue = self._query(
            "SELECT f.id cid, f.last_name, f.first_name, SUM(p.remaining_amount) r "
            "FROM payments p JOIN families f ON p.family_id=f.id "
            "WHERE p.remaining_amount>0 "
            "GROUP BY f.id, f.last_name, f.first_name "
            "ORDER BY r DESC LIMIT 8",
            default=[])
        if overdue:
            for r in overdue:
                name = f"{r.get('last_name','') or ''} {r.get('first_name','') or ''}".strip() or "—"
                self.alerts_layout.addWidget(
                    self._client_row(name, f"{float(r.get('r',0) or 0):.2f} €",
                                     "#C62828", r.get('cid')))
        else:
            empty = QLabel("✓  Καμία εκκρεμής οφειλή")
            empty.setStyleSheet("border:none;color:#2E7D32;font-size:13px;padding:8px 2px;")
            self.alerts_layout.addWidget(empty)

        # Πακέτα που λήγουν σύντομα (εντός 30 ημερών, με υπόλοιπο ώρες)
        _exp_title = self._section_title("📦  Πακέτα που λήγουν  ›")
        _exp_title.setCursor(Qt.PointingHandCursor)
        _exp_title.setToolTip("Άνοιγμα οθόνης «Λήξεις Πακέτων»")
        _exp_title.mousePressEvent = lambda e: self.open_expirations.emit()
        self.alerts_layout.addWidget(_exp_title)
        expiring = self._query(
            "SELECT f.id cid, f.last_name, f.first_name, cph.expiry_date exp, "
            "cph.remaining_hours rem, DATEDIFF(cph.expiry_date, CURDATE()) days "
            "FROM client_package_hours cph JOIN families f ON cph.client_id=f.id "
            "WHERE cph.is_active=1 AND cph.remaining_hours>0 "
            "AND cph.expiry_date IS NOT NULL "
            "AND cph.expiry_date >= CURDATE() "
            "AND cph.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY) "
            "ORDER BY cph.expiry_date ASC LIMIT 8",
            default=[])
        if expiring:
            for r in expiring:
                name = f"{r.get('last_name','') or ''} {r.get('first_name','') or ''}".strip() or "—"
                days = int(r.get('days') or 0)
                rem = float(r.get('rem') or 0)
                exp = r.get('exp')
                exp_s = exp.strftime('%d/%m/%Y') if hasattr(exp, 'strftime') else str(exp or '')
                left = f"{name}  ·  {_fmt_hours_min(rem)}"
                pill = "λήγει σήμερα" if days == 0 else f"{days} μέρες"
                row = self._client_row(left, pill, "#EF6C00", r.get('cid'))
                row.setToolTip(f"Λήξη πακέτου: {exp_s} — άνοιγμα «Λήξεις Πακέτων»")
                row.setCursor(Qt.PointingHandCursor)
                row.mousePressEvent = lambda ev: self.open_expirations.emit()
                self.alerts_layout.addWidget(row)
        else:
            empty2 = QLabel("✓  Κανένα πακέτο δεν λήγει σύντομα")
            empty2.setStyleSheet("border:none;color:#2E7D32;font-size:13px;padding:8px 2px;")
            self.alerts_layout.addWidget(empty2)

        self.alerts_layout.addStretch()

    def _load_recent(self):
        self._clear_layout(self.recent_layout)
        self.recent_layout.addWidget(self._section_title("🕑 Πρόσφατες Συνεδρίες"))
        hint = QLabel("Κάντε κλικ σε μια συνεδρία για λεπτομέρειες")
        hint.setStyleSheet("border:none;color:#9AA0A6;font-size:11px;margin:0 0 6px 2px;")
        self.recent_layout.addWidget(hint)
        rows = self._query(
            "SELECT s.id, s.start_time, s.end_time et, s.duration_minutes dm, "
            "s.billed_amount ba, s.status st, s.session_type stype, "
            "s.technician tech, s.description descr, "
            "f.last_name, f.first_name "
            "FROM support_sessions s "
            "LEFT JOIN families f ON s.client_id=f.id "
            "ORDER BY s.start_time DESC LIMIT 8", default=[])
        if not rows:
            self.recent_layout.addWidget(self._sub_label("  Καμία συνεδρία ακόμα", muted=True))
            return
        for r in rows:
            self.recent_layout.addWidget(self._session_row(r))

    def _session_row(self, sdata):
        status = sdata.get("st")
        color = _STATUS_COLOR.get(status, "#455A64")
        name = f"{sdata.get('last_name','') or ''} {sdata.get('first_name','') or ''}".strip() or "—"
        when = sdata.get("start_time")
        when_s = when.strftime("%d/%m/%Y %H:%M") if hasattr(when, "strftime") else str(when or "")
        dm = int(sdata.get("dm", 0) or 0)
        ba = float(sdata.get("ba", 0) or 0)
        dur_txt = f"{dm // 60}ω {dm % 60}λ" if dm >= 60 else f"{dm}λ"
        st_txt = SESSION_STATUS.get(status, status or "—")

        w = QFrame()
        w.setObjectName("recRow")
        w.setStyleSheet(
            "#recRow{border:none;border-radius:6px;background:transparent;}"
            "#recRow:hover{background:#F1F5FB;}")
        h = QHBoxLayout(w)
        h.setContentsMargins(8, 6, 8, 6)
        h.setSpacing(8)
        dot = QLabel("●")
        dot.setAttribute(Qt.WA_TransparentForMouseEvents)
        dot.setStyleSheet(f"border:none;color:{color};font-size:10px;")
        left = QLabel(f"<b>{name}</b>  <span style='color:#90A4AE'>· {when_s}</span>")
        left.setAttribute(Qt.WA_TransparentForMouseEvents)
        left.setStyleSheet("border:none;font-size:13px;color:#1F3B57;")
        pill_text = f"{dur_txt}  ·  {ba:.2f}€" if ba > 0 else dur_txt
        pill = QLabel(pill_text)
        pill.setAttribute(Qt.WA_TransparentForMouseEvents)
        pill.setStyleSheet(
            f"border:none;font-size:12px;font-weight:bold;color:{color};"
            f"background:{self._tint(color)};border-radius:10px;padding:2px 10px;")
        stlbl = QLabel(st_txt)
        stlbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        stlbl.setStyleSheet(f"border:none;font-size:12px;color:{color};")
        h.addWidget(dot)
        h.addWidget(left)
        h.addStretch()
        h.addWidget(pill)
        h.addWidget(stlbl)
        w.setCursor(Qt.PointingHandCursor)
        w.setToolTip("Λεπτομέρειες συνεδρίας")
        def press(ev, sess=sdata):
            self._open_session_details(sess)
        w.mousePressEvent = press
        return w

    def _open_session_details(self, sdata):
        try:
            SessionDetailsDialog(sdata, self).exec()
        except Exception as e:
            logger.error(f"open session details failed: {e}", exc_info=True)

    # ---------- small widgets ----------
    def _tint(self, color):
        """Light background tint for an amount pill."""
        return {"#C62828": "#FDECEA", "#EF6C00": "#FFF3E0",
                "#2E7D32": "#E8F5E9", "#1976D2": "#E3F2FD",
                "#90A4AE": "#ECEFF1", "#455A64": "#ECEFF1"}.get(color, "#F0F0F0")

    def _client_row(self, left, right, color, client_id):
        """A clickable alert row: click -> open the client in the Οφειλές screen."""
        w = QFrame()
        w.setObjectName("alertRow")
        w.setStyleSheet(
            "#alertRow{border:none;border-radius:6px;background:transparent;}"
            "#alertRow:hover{background:#F1F5FB;}")
        h = QHBoxLayout(w)
        h.setContentsMargins(8, 6, 8, 6)
        h.setSpacing(8)
        dot = QLabel("●")
        dot.setAttribute(Qt.WA_TransparentForMouseEvents)
        dot.setStyleSheet(f"border:none;color:{color};font-size:10px;")
        l = QLabel(left)
        l.setAttribute(Qt.WA_TransparentForMouseEvents)
        l.setStyleSheet("border:none;font-size:13px;color:#1F3B57;font-weight:500;")
        r = QLabel(right)
        r.setAttribute(Qt.WA_TransparentForMouseEvents)
        r.setStyleSheet(
            f"border:none;font-size:12px;font-weight:bold;color:{color};"
            f"background:{self._tint(color)};border-radius:10px;padding:2px 10px;")
        h.addWidget(dot)
        h.addWidget(l)
        h.addStretch()
        h.addWidget(r)
        if client_id is not None:
            w.setCursor(Qt.PointingHandCursor)
            w.setToolTip("Άνοιγμα στην οθόνη Οφειλών")
            def press(ev, cid=client_id):
                self.open_client_in_debts.emit(int(cid))
            w.mousePressEvent = press
        return w

    def _sub_label(self, text, muted=False):
        lbl = QLabel(text)
        color = "#999" if muted else "#333"
        lbl.setStyleSheet(f"border:none;color:{color};font-size:12px;margin-top:4px;")
        return lbl

    def _row_label(self, left, right, color):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(2, 1, 2, 1)
        l = QLabel(left)
        l.setStyleSheet("border:none;font-size:12px;color:#333;")
        r = QLabel(right)
        r.setStyleSheet(f"border:none;font-size:12px;font-weight:bold;color:{color};")
        h.addWidget(l)
        h.addStretch()
        h.addWidget(r)
        return w


class SessionDetailsDialog(QDialog):
    """Read-only details of a single support session (opened from the dashboard)."""

    def __init__(self, sdata, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Λεπτομέρειες Συνεδρίας #{sdata.get('id','')}")
        self.setMinimumWidth(460)
        self._build(sdata)

    def _build(self, s):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        name = f"{s.get('last_name','') or ''} {s.get('first_name','') or ''}".strip() or "—"
        title = QLabel(name)
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1F3B57;")
        lay.addWidget(title)

        def dt(v):
            return v.strftime("%d/%m/%Y %H:%M") if hasattr(v, "strftime") else (str(v) if v else "—")

        dm = int(s.get("dm", 0) or 0)
        dur = f"{dm // 60} ώρες {dm % 60} λεπτά" if dm >= 60 else f"{dm} λεπτά"
        ba = float(s.get("ba", 0) or 0)

        grp = QGroupBox("Στοιχεία Συνεδρίας")
        form = QFormLayout(grp)
        form.setSpacing(6)
        form.addRow("Κωδικός:", QLabel(str(s.get("id", "—"))))
        form.addRow("Πελάτης:", QLabel(name))
        form.addRow("Τύπος:", QLabel(SESSION_TYPE.get(s.get("stype"), s.get("stype") or "—")))
        form.addRow("Κατάσταση:", QLabel(SESSION_STATUS.get(s.get("st"), s.get("st") or "—")))
        form.addRow("Έναρξη:", QLabel(dt(s.get("start_time"))))
        form.addRow("Λήξη:", QLabel(dt(s.get("et"))))
        form.addRow("Διάρκεια:", QLabel(dur))
        form.addRow("Τεχνικός:", QLabel(str(s.get("tech") or "—")))
        form.addRow("Χρέωση:", QLabel(f"{ba:.2f} €"))
        lay.addWidget(grp)

        descr = s.get("descr") or ""
        if descr:
            g2 = QGroupBox("Περιγραφή / Σημειώσεις")
            v = QVBoxLayout(g2)
            te = QTextEdit()
            te.setPlainText(str(descr))
            te.setReadOnly(True)
            te.setMaximumHeight(120)
            v.addWidget(te)
            lay.addWidget(g2)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.button(QDialogButtonBox.Close).setText("Κλείσιμο")
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)
        lay.addWidget(btns)
