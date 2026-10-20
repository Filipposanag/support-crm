# -*- coding: utf-8 -*-
"""
Payment model for Support CRM.
"""

from dataclasses import dataclass
from datetime import date, time
from typing import Optional
from decimal import Decimal


@dataclass
class Payment:
    """Payment data model."""
    id: Optional[int] = None
    family_id: int = 0
    legacy_code: Optional[int] = None
    legacy_pcode: int = 0
    payment_date: Optional[date] = None
    payment_time: Optional[time] = None
    description: str = ''
    receipt_no: str = ''
    remarks: str = ''
    total_amount: Decimal = Decimal('0.00')
    paid_amount: Decimal = Decimal('0.00')
    remaining_amount: Decimal = Decimal('0.00')
    status: str = 'UNPAID'  # PAID, PARTIAL, UNPAID
    year: Optional[int] = None
    
    def calculate_status(self):
        """Calculate payment status based on amounts."""
        self.remaining_amount = self.total_amount - self.paid_amount
        
        if self.remaining_amount <= 0:
            self.status = 'PAID'
        elif self.paid_amount > 0:
            self.status = 'PARTIAL'
        else:
            self.status = 'UNPAID'
    
    def get_status_display(self) -> str:
        """Get localized status display."""
        status_map = {
            'PAID': 'Εξοφλημένο',
            'PARTIAL': 'Μερική',
            'UNPAID': 'Ανεξόφλητο'
        }
        return status_map.get(self.status, self.status)
