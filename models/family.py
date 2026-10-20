# -*- coding: utf-8 -*-
"""
Family model for Support CRM.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Family:
    """Family data model."""
    id: Optional[int] = None
    legacy_code: int = 0
    last_name: str = ''
    first_name: str = ''
    father_name: str = ''  # Όνομα Πατρός
    spouse_first_name: str = ''
    spouse_last_name: str = ''
    spouse_father_name: str = ''
    spouse_maiden_name: str = ''  # Γένος Συζύγου
    national_id: str = ''
    profession: str = ''
    address: str = ''
    city: str = ''
    postal_code: str = ''
    phone: str = ''
    mobile: str = ''
    email: str = ''
    birth_date: Optional[date] = None
    members_count: int = 0
    notes: str = ''
    is_active: bool = True
    is_divorced: bool = False  # Διαζευγμένοι
    spouse_deceased: bool = False  # Αποθανών/ούσα σύζυγος
    is_association_member: bool = False  # Μέλος Συλλόγου (δωρεάν συνδρομή)
    
    def get_full_name(self) -> str:
        """Get full name (last_name first_name)."""
        return f"{self.last_name} {self.first_name}".strip()
    
    def get_spouse_full_name(self) -> str:
        """Get spouse full name."""
        if self.spouse_first_name or self.spouse_last_name:
            return f"{self.spouse_last_name} {self.spouse_first_name}".strip()
        return ''
