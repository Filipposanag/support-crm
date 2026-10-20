# -*- coding: utf-8 -*-
"""
Payments table model for Support CRM.
"""

import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

logger = logging.getLogger(__name__)


class PaymentsTableModel(QAbstractTableModel):
    """Table model for displaying payment records."""
    
    # Column definitions
    COLUMNS = [
        ('payment_date', 'Ημερομηνία'),
        ('family_code', 'Κωδικός'),
        ('family_name', 'Πελάτης'),
        ('description', 'Περιγραφή'),
        ('subscription_start_date', 'Έναρξη Πακέτου'),
        ('subscription_end_date', 'Λήξη Πακέτου'),
        ('total_amount', 'Ποσό'),
        ('paid_amount', 'Πληρωμένο'),
        ('remaining_amount', 'Υπόλοιπο'),
        ('status', 'Κατάσταση'),
        ('receipt_no', 'Αριθμός Απόδειξης'),
    ]
    
    # Status colors
    STATUS_COLORS = {
        'paid': QColor(76, 175, 80),      # Green
        'partial': QColor(255, 152, 0),   # Orange
        'unpaid': QColor(244, 67, 54),    # Red
    }
    
    def __init__(self, parent=None):
        """Initialize the payments table model."""
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._status_display_map = {
            'paid': 'Εξοφλημένο',
            'partial': 'Μερικώς',
            'unpaid': 'Ανεξόφλητο',
            'pending': 'Σε εκκρεμότητα',
            'cancelled': 'Ακυρωμένο',
            'canceled': 'Ακυρωμένο',
            'completed': 'Ολοκληρωμένο',
            'overdue': 'Ληξιπρόθεσμο',
            '': '—',
        }
        logger.debug("PaymentsTableModel initialized")
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """Return the number of rows."""
        if parent.isValid():
            return 0
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        """Return the number of columns."""
        if parent.isValid():
            return 0
        return len(self.COLUMNS)
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        """Return data for the given index and role."""
        if not index.isValid():
            return None
        
        if index.row() >= len(self._data) or index.row() < 0:
            return None
        
        row_data = self._data[index.row()]
        column_key = self.COLUMNS[index.column()][0]
        
        # Display role - show the data
        if role == Qt.DisplayRole:
            value = row_data.get(column_key)
            
            # Format specific columns
            if column_key == 'payment_date' and value:
                return str(value)
            elif column_key in ('total_amount', 'paid_amount', 'remaining_amount'):
                if value is not None:
                    # Convert to Decimal if needed
                    if not isinstance(value, Decimal):
                        value = Decimal(str(value))
                    return f"{value:.2f} €"
                return "0.00 €"
            elif column_key == 'status':
                # Normalize status to lowercase
                raw_status = row_data.get('status', 'unpaid')
                normalized_status = str(raw_status).strip().lower()
                return self._status_display_map.get(normalized_status, 'Άγνωστη')
            elif value is None:
                return ""
            else:
                return str(value)
        
        # Text alignment
        elif role == Qt.TextAlignmentRole:
            if column_key in ('total_amount', 'paid_amount', 'remaining_amount'):
                return Qt.AlignRight | Qt.AlignVCenter
            elif column_key == 'status':
                return Qt.AlignCenter | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter
        
        # Foreground color for status column (white text)
        elif role == Qt.ForegroundRole:
            if column_key == 'status':
                return QColor(255, 255, 255)  # White text
        
        # Background color for status column
        elif role == Qt.BackgroundRole:
            if column_key == 'status':
                # Normalize status to lowercase
                raw_status = row_data.get('status', 'unpaid')
                normalized_status = str(raw_status).strip().lower()
                return self.STATUS_COLORS.get(normalized_status)
        
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        """Return header data."""
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if 0 <= section < len(self.COLUMNS):
                    return self.COLUMNS[section][1]
            elif orientation == Qt.Vertical:
                return str(section + 1)
        
        return None
    
    def set_payments(self, payments: List[Dict[str, Any]]):
        """Set the payment data for the model."""
        self.beginResetModel()
        # Ensure _data is always a list (not tuple) so it can be sorted
        self._data = list(payments) if payments else []
        self.endResetModel()
        logger.debug(f"PaymentsTableModel loaded {len(payments)} payments")
    
    def get_payment_at_row(self, row: int) -> Optional[Dict[str, Any]]:
        """Get the payment data at the specified row."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None
    
    def clear(self):
        """Clear all data from the model."""
        self.beginResetModel()
        self._data = []
        self.endResetModel()
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder):
        """
        Sort the model by the specified column.
        
        Args:
            column: Column index to sort by
            order: Sort order (Ascending or Descending)
        """
        from datetime import date
        from decimal import Decimal
        
        self.layoutAboutToBeChanged.emit()
        
        reverse = (order == Qt.DescendingOrder)
        
        # Define sort keys for each column
        def get_sort_key(payment):
            if column == 0:  # ID
                return payment.get('id', 0)
            elif column == 1:  # Αρ. Απόδειξης
                return payment.get('receipt_no', '')
            elif column == 2:  # Ημερομηνία
                return payment.get('payment_date') or date.min
            elif column == 3:  # Πελάτης
                return payment.get('family_name', '')
            elif column == 4:  # Περιγραφή
                return payment.get('description', '')
            elif column == 5:  # Σύνολο
                return payment.get('total_amount', Decimal('0'))
            elif column == 6:  # Πληρωμένο
                return payment.get('paid_amount', Decimal('0'))
            elif column == 7:  # Κατάσταση
                return payment.get('status', '')
            return ''
        
        self._data.sort(key=get_sort_key, reverse=reverse)
        
        self.layoutChanged.emit()
        logger.debug(f"Sorted by column {column}, order={'DESC' if reverse else 'ASC'}")
        logger.debug("PaymentsTableModel cleared")
    
    def refresh_row(self, row: int, payment_data: Dict[str, Any]):
        """Refresh a specific row with updated payment data."""
        if 0 <= row < len(self._data):
            self._data[row] = payment_data
            # Emit dataChanged for the entire row
            left_index = self.index(row, 0)
            right_index = self.index(row, self.columnCount() - 1)
            self.dataChanged.emit(left_index, right_index)
            logger.debug(f"Refreshed row {row} in PaymentsTableModel")
