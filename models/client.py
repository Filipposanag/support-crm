# -*- coding: utf-8 -*-
"""
Client model for Support CRM.
Represents a support client with RustDesk integration.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional
from decimal import Decimal


@dataclass
class Client:
    """Client data model for support management."""
    id: Optional[int] = None
    legacy_code: int = 0  # Client number/code
    last_name: str = ''
    first_name: str = ''
    company_name: str = ''  # Company/Organization name
    national_id: str = ''  # Tax ID / VAT number
    afm: str = ''  # ΑΦΜ - Tax ID (for invoices)
    doy: str = ''  # ΔΟΥ - Tax office (for invoices)
    profession: str = ''
    address: str = ''
    city: str = ''
    postal_code: str = ''
    phone: str = ''
    mobile: str = ''
    email: str = ''
    notes: str = ''
    notes_support: str = ''  # Support-specific notes
    is_active: bool = True
    
    # RustDesk Integration
    rustdesk_id: str = ''  # RustDesk client ID
    rustdesk_password: str = ''  # RustDesk password (encrypted)
    
    # Support Plan & Billing
    support_plan: str = 'hourly'  # hourly, monthly, yearly, custom
    hourly_rate: Decimal = Decimal('0.00')  # Hourly support rate
    monthly_rate: Decimal = Decimal('0.00')  # Monthly subscription rate
    
    def get_full_name(self) -> str:
        """Get full name or company name."""
        if self.company_name:
            return self.company_name
        return f"{self.last_name} {self.first_name}".strip()
    
    def get_display_name(self) -> str:
        """Get display name for UI."""
        if self.company_name:
            return f"{self.company_name} ({self.first_name} {self.last_name})".strip()
        return self.get_full_name()
    
    def has_rustdesk_configured(self) -> bool:
        """Check if RustDesk is configured for this client."""
        return bool(self.rustdesk_id and self.rustdesk_id.strip())
    
    def get_support_plan_display(self) -> str:
        """Get human-readable support plan name."""
        plans = {
            'hourly': 'Ωριαία Χρέωση',
            'monthly': 'Μηνιαία Συνδρομή',
            'yearly': 'Ετήσια Συνδρομή',
            'custom': 'Προσαρμοσμένο'
        }
        return plans.get(self.support_plan, self.support_plan)


@dataclass
class SupportSession:
    """Support session data model."""
    id: Optional[int] = None
    client_id: int = 0
    session_type: str = 'remote'  # remote, onsite, phone, email
    start_time: Optional[date] = None
    end_time: Optional[date] = None
    duration_minutes: int = 0
    duration_seconds: int = 0
    rustdesk_session_id: str = ''
    technician: str = ''
    description: str = ''
    issue_summary: str = ''
    status: str = 'active'  # active, completed, cancelled
    billed_amount: Decimal = Decimal('0.00')
    payment_id: Optional[int] = None
    
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.status == 'active' and self.end_time is None
    
    def get_session_type_display(self) -> str:
        """Get human-readable session type."""
        types = {
            'remote': 'Απομακρυσμένη (RustDesk)',
            'onsite': 'Επιτόπου',
            'phone': 'Τηλεφωνική',
            'email': 'Email/Chat'
        }
        return types.get(self.session_type, self.session_type)
    
    def get_status_display(self) -> str:
        """Get human-readable status."""
        statuses = {
            'active': 'Ενεργή',
            'completed': 'Ολοκληρωμένη',
            'cancelled': 'Ακυρωμένη'
        }
        return statuses.get(self.status, self.status)
