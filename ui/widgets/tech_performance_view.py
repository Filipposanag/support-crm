# -*- coding: utf-8 -*-
"""
Απόδοση Τεχνικών — admin-only performance dashboard.
Aggregates support_sessions per technician: number of sessions, total hours,
average duration, split by type (RustDesk / Τηλεφωνική), distinct clients
served and billed charges. Same visual style as the Αρχική dashboard.
"""
import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QComboBox, QPushButton, QScrollArea, QSizePolicy, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QToolTip,
)

logger = logging.getLogger(__name__)

CHARTS_OK = True
try:
    from PySide6.QtCharts import (
        QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis,
    )
    from PySide6.QtGui import QPainter
except Exception as _e:  # pragma: no cover
    CHARTS_OK = False
    logger.warning(f"QtCharts not available, charts will be hidden: {_e}")


class TechPerformanceView(QWidget):
    """Admin-only technician performance dashboard."""

    PERIODS = [
        ("Τελευταίες 30 ημέρες", 30),
        ("Τελευταίες 90 ημέρες", 90),
        ("Τελευταίοι 6 μήνες", 180),
        ("Όλα", 100000),
    ]

    def __init__(self, db_connection, tr_manager=None, parent=None):
        super().__init__(parent)
        self.db = db_connection
        self.tr_manager = tr_manager
        self._kpi = {}
        self._build_ui()
        self.refresh()

    # ---------- data ----------
    def _query(self, sql, params=None):
        try:
            rows = self.db.execute_query(sql, params)
            return rows or []
        except Exception as e:
            logger.error(f"TechPerformance query failed: {e}")
            return []

    def _period_days(self):
        return self.PERIODS[self.period_combo.currentIndex()][1]

    # ---------- UI ----------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        root = QVBoxLayout(body)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        head = QHBoxLayout()
        title = QLabel("Απόδοση Τεχνικών")
        title.setStyleSheet("font-size:22px;font-weight:bold;color:#212121;")
        head.addWidget(title)
        head.addStretch(1)
        period_lbl = QLabel("Περίοδος:")
        period_lbl.setStyleSheet("color:#555;")
        head.addWidget(period_lbl)
        self.period_combo = QComboBox()
        self.period_combo.setMinimumWidth(180)
        for lbl, _d in self.PERIODS:
            self.period_combo.addItem(lbl)
        self.period_combo.setCurrentIndex(2)
        self.period_combo.currentIndexChanged.connect(lambda *_: self.refresh())
        head.addWidget(self.period_combo)
        refresh_btn = QPushButton("↻ Ανανέωση")
        refresh_btn.clicked.connect(self.refresh)
        head.addWidget(refresh_btn)
        root.addLayout(head)

        sub = QLabel("Στατιστικά συνεδριών ανά τεχνικό. Ορατό μόνο στον διαχειριστή.")
        sub.setStyleSheet("color:#666;font-size:12px;")
        root.addWidget(sub)

        # KPI cards
        kpi = QGridLayout()
        kpi.setSpacing(12)
        specs = [
            ("techs", "Ενεργοί τεχνικοί", "#1976D2"),
            ("sessions", "Συνεδρίες", "#2E7D32"),
            ("hours", "Συνολικές ώρες", "#F9A825"),
            ("avg", "Μ.Ο. διάρκειας (λεπτά)", "#6A1B9A"),
        ]
        for i, (k, l, c) in enumerate(specs):
            kpi.addWidget(self._make_card(k, l, c), 0, i)
            kpi.setColumnStretch(i, 1)
        root.addLayout(kpi)

        # charts
        charts = QHBoxLayout()
        charts.setSpacing(16)
        self.chart1_box, self.chart1_holder = self._chart_box("Συνεδρίες ανά τεχνικό")
        self.chart2_box, self.chart2_holder = self._chart_box("Ώρες ανά τεχνικό")
        charts.addWidget(self.chart1_box)
        charts.addWidget(self.chart2_box)
        root.addLayout(charts)

        # detail table
        tbl_title = QLabel("Αναλυτικά ανά τεχνικό")
        tbl_title.setStyleSheet("font-size:15px;font-weight:bold;color:#212121;margin-top:6px;")
        root.addWidget(tbl_title)
        self.table = QTableWidget()
        cols = ["Τεχνικός", "Συνεδρίες", "Ώρες", "Μ.Ο. (λεπτά)",
                "RustDesk", "Τηλεφωνικές", "Πελάτες", "Χρεώσεις (€)"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(cols)):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(220)
        root.addWidget(self.table)
        root.addStretch(1)

    def _make_card(self, key, label, color):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:white;border:1px solid #E0E0E0;border-left:5px solid {color};"
            f"border-radius:8px;}}")
        card.setMinimumHeight(90)
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 12, 16, 12)
        val = QLabel("—")
        val.setStyleSheet(f"font-size:26px;font-weight:bold;color:{color};border:none;")
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size:12px;color:#555;border:none;")
        lbl.setWordWrap(True)
        v.addWidget(val)
        v.addWidget(lbl)
        self._kpi[key] = val
        return card

    def _chart_box(self, title):
        box = QFrame()
        box.setStyleSheet("QFrame{background:white;border:1px solid #E0E0E0;border-radius:8px;}")
        box.setMinimumHeight(300)
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v = QVBoxLayout(box)
        t = QLabel(title)
        t.setStyleSheet("font-size:14px;font-weight:bold;color:#212121;border:none;")
        v.addWidget(t)
        holder = QVBoxLayout()
        v.addLayout(holder)
        return box, holder

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())

    # ---------- refresh ----------
    def refresh(self):
        days = self._period_days()
        rows = self._query(
            "SELECT technician, COUNT(*) AS sessions, "
            "COALESCE(SUM(duration_minutes),0) AS total_min, "
            "COALESCE(AVG(duration_minutes),0) AS avg_min, "
            "COALESCE(SUM(session_type='remote'),0) AS remote_cnt, "
            "COALESCE(SUM(session_type='phone'),0) AS phone_cnt, "
            "COUNT(DISTINCT client_id) AS clients, "
            "COALESCE(SUM(billed_amount),0) AS revenue "
            "FROM support_sessions "
            "WHERE status='completed' AND technician IS NOT NULL AND technician<>'' "
            "AND start_time >= (CURDATE() - INTERVAL %s DAY) "
            "GROUP BY technician ORDER BY sessions DESC",
            (days,))

        total_sessions = sum(int(r['sessions']) for r in rows)
        total_min = sum(float(r['total_min']) for r in rows)
        avg_min = (total_min / total_sessions) if total_sessions else 0
        self._kpi['techs'].setText(str(len(rows)))
        self._kpi['sessions'].setText(str(total_sessions))
        self._kpi['hours'].setText(f"{total_min/60:.1f}")
        self._kpi['avg'].setText(f"{avg_min:.0f}")

        self.table.setRowCount(0)
        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)
            vals = [
                str(r['technician'] or "—"),
                str(int(r['sessions'])),
                f"{float(r['total_min'])/60:.1f}",
                f"{float(r['avg_min']):.0f}",
                str(int(r['remote_cnt'])),
                str(int(r['phone_cnt'])),
                str(int(r['clients'])),
                f"{float(r['revenue']):.2f}",
            ]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c > 0:
                    it.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, c, it)

        self._draw_bar(self.chart1_holder, rows, lambda r: int(r['sessions']),
                       "Συνεδρίες", "#1976D2", "sessions")
        self._draw_bar(self.chart2_holder, rows, lambda r: round(float(r['total_min'])/60, 1),
                       "Ώρες", "#F9A825", "hours")

    def _draw_bar(self, holder, rows, valfn, series_name, color, unit):
        self._clear_layout(holder)
        if not CHARTS_OK:
            fb = QLabel("Τα γραφήματα δεν είναι διαθέσιμα (QtCharts).")
            fb.setStyleSheet("color:#888;border:none;")
            holder.addWidget(fb)
            return
        if not rows:
            fb = QLabel("Δεν υπάρχουν δεδομένα για την περίοδο.")
            fb.setStyleSheet("color:#888;border:none;")
            holder.addWidget(fb)
            return
        bar_set = QBarSet(series_name)
        cats = []
        for r in rows:
            bar_set.append(valfn(r))
            cats.append(str(r['technician'] or "—"))
        bar_set.setColor(QColor(color))
        series = QBarSeries()
        series.append(bar_set)
        series.setLabelsVisible(False)
        # tooltip on hover (like the Αρχική dashboard)
        series.hovered.connect(
            lambda status, index, bs, u=unit, labels=list(cats): self._on_bar_hovered(status, index, bs, u, labels))
        chart = QChart()
        chart.addSeries(series)
        chart.legend().setVisible(False)
        chart.setBackgroundVisible(False)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        axis_x = QBarCategoryAxis()
        axis_x.append(cats)
        axis_x.setLabelsAngle(-25)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)
        axis_y = QValueAxis()
        mx = max((valfn(r) for r in rows), default=0) or 0
        axis_y.setRange(0, mx if mx > 0 else 10)
        axis_y.setTickCount(6)
        axis_y.setLabelFormat("%d")
        axis_y.applyNiceNumbers()
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(240)
        view.setStyleSheet("border:none;")
        holder.addWidget(view)

    def _on_bar_hovered(self, status, index, barset, unit, labels):
        """Show a tooltip with the exact value of the hovered bar."""
        try:
            if status and barset is not None and 0 <= index < barset.count():
                val = float(barset.at(index))
                who = labels[index] if 0 <= index < len(labels) else ""
                if unit == "hours":
                    body = f"{val:.1f} ώρες"
                else:
                    body = f"{int(round(val))} συνεδρίες"
                QToolTip.showText(QCursor.pos(), (f"{who} — " if who else "") + body)
            else:
                QToolTip.hideText()
        except Exception:
            pass
