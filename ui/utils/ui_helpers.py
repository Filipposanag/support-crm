"""
UI Helper Functions
Provides utility functions for consistent UI styling and behavior.
"""

from PySide6.QtCore import Qt, QEvent, QObject
from PySide6.QtWidgets import QAbstractItemView
from PySide6.QtGui import QKeySequence


def style_table(table, column_widths=None):
    """
    Apply consistent styling to a QTableView.
    
    Args:
        table: QTableView instance to style
        column_widths: Optional dict mapping column index to width
                      e.g., {0: 80, 1: 160, 2: 130}
    
    Example:
        style_table(self.table_view, {0: 80, 1: 160, 2: 130})
    """
    # Enable alternating row colors
    table.setAlternatingRowColors(True)
    
    # Vertical header (row numbers)
    vh = table.verticalHeader()
    vh.setDefaultSectionSize(34)
    vh.setMinimumSectionSize(34)
    vh.setVisible(False)
    
    # Horizontal header (column headers)
    hh = table.horizontalHeader()
    hh.setStretchLastSection(False)
    hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    hh.setDefaultSectionSize(150)
    hh.setMinimumSectionSize(100)
    
    # Apply custom column widths if provided
    if column_widths:
        for col_index, width in column_widths.items():
            table.setColumnWidth(col_index, width)


def style_families_table(table):
    """
    Apply styling specific to families table.
    
    Args:
        table: QTableView instance for families
    """
    column_widths = {
        0: 80,   # Κωδικός
        1: 160,  # Επώνυμο
        2: 130,  # Όνομα
        3: 120,  # Τηλέφωνο
        4: 120,  # ΑΣΠΕ
        5: 120,  # Πόλη
        6: 70,   # Μέλη
        7: 100,  # Ενεργός
    }
    style_table(table, column_widths)


def style_payments_table(table):
    """
    Apply styling specific to payments table.
    
    Args:
        table: QTableView instance for payments
    """
    column_widths = {
        0: 80,   # ID
        1: 160,  # Πελάτης
        2: 110,  # Ημερομηνία
        3: 150,  # Περιγραφή
        4: 100,  # Συνολικό
        5: 100,  # Πληρωμένο
        6: 100,  # Υπόλοιπο
        7: 80,   # Έτος
    }
    style_table(table, column_widths)


def style_report_table(table):
    """
    Apply styling specific to subscription report table.
    
    Args:
        table: QTableView instance for reports
    """
    column_widths = {
        0: 80,   # Κωδικός
        1: 180,  # Πελάτης
        2: 120,  # Πόλη
        3: 70,   # Μέλη
        4: 100,  # Χρεωθέν
        5: 100,  # Πληρωμένο
        6: 100,  # Υπόλοιπο
    }
    style_table(table, column_widths)


def style_table_widget(table_widget):
    """
    Apply consistent styling to a QTableWidget.
    
    This provides the same styling as QTableView for consistency across the application.
    
    Args:
        table_widget: QTableWidget instance to style
    
    Example:
        style_table_widget(self.table)
    """
    # Enable alternating row colors
    table_widget.setAlternatingRowColors(True)
    
    # Vertical header (row numbers)
    vh = table_widget.verticalHeader()
    vh.setDefaultSectionSize(34)
    vh.setMinimumSectionSize(34)
    vh.setVisible(False)
    
    # Horizontal header (column headers)
    hh = table_widget.horizontalHeader()
    hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    hh.setStretchLastSection(False)


# Calendar styling functions removed - using default Qt behavior


def enable_multi_selection(table_view):
    """
    Enable multi-selection on a QTableView or QTableWidget.
    
    Features:
    - Ctrl+A to select all rows
    - Ctrl+Click to select multiple rows
    - Shift+Click to select range
    - Click to select single row
    
    Args:
        table_view: QTableView or QTableWidget instance
    
    Example:
        enable_multi_selection(self.table_view)
    """
    # Enable extended selection mode (allows Ctrl+Click and Shift+Click)
    table_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
    
    # Ensure row selection behavior
    table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
    
    # Install event filter for Ctrl+A
    if not hasattr(table_view, '_multi_select_filter'):
        table_view._multi_select_filter = MultiSelectEventFilter(table_view)
        table_view.installEventFilter(table_view._multi_select_filter)


class MultiSelectEventFilter(QObject):
    """Event filter to handle Ctrl+A for select all."""
    
    def __init__(self, table_view):
        super().__init__(table_view)
        self.table_view = table_view
    
    def eventFilter(self, obj, event):
        """Handle key press events for Ctrl+A."""
        if event.type() == QEvent.KeyPress:
            # Check for Ctrl+A
            if event.matches(QKeySequence.SelectAll):
                self.table_view.selectAll()
                return True  # Event handled
        
        return False  # Let other events pass through


def gr_question(parent, title, text, buttons=None, default_button=None):
    """QMessageBox.question with Greek standard buttons (Ναι/Όχι/OK/Άκυρο).
    Drop-in for QMessageBox.question(parent, title, text, buttons, defaultButton);
    returns the clicked QMessageBox.StandardButton."""
    from PySide6.QtWidgets import QMessageBox
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons if buttons is not None else (QMessageBox.Yes | QMessageBox.No))
    labels = {
        QMessageBox.Yes: "Ναι", QMessageBox.No: "Όχι", QMessageBox.Ok: "OK",
        QMessageBox.Cancel: "Άκυρο", QMessageBox.Save: "Αποθήκευση",
        QMessageBox.Discard: "Απόρριψη", QMessageBox.Close: "Κλείσιμο",
    }
    for std, gr in labels.items():
        b = box.button(std)
        if b is not None:
            b.setText(gr)
    if default_button is not None:
        box.setDefaultButton(default_button)
    return box.exec()


def fmt_hours_min(h):
    """Format decimal hours as Greek hours/minutes: 0.7->'42 λεπτά', 5.0->'5 ώρες', 9.3->'9 ώρες 18 λεπτά'."""
    if h is None:
        return "-"
    try:
        total_min = int(round(float(h) * 60))
    except (TypeError, ValueError):
        return "-"
    if total_min <= 0:
        return "-"
    hh, mm = divmod(total_min, 60)
    wname = "ώρα" if hh == 1 else "ώρες"
    if hh and mm:
        return f"{hh} {wname} {mm} λεπτά"
    if hh:
        return f"{hh} {wname}"
    return f"{mm} λεπτά"
