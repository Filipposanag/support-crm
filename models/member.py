"""
Member data model for SupportCRM.

This module defines the Member dataclass representing an individual member
of a family in the system with validation logic.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List


@dataclass
class Member:
    """
    Represents an individual member of a family in the Support CRM system.
    
    Attributes correspond to the members table in the database.
    """
    id: Optional[int] = None
    family_id: int = 0
    legacy_family_code: int = 0
    inner_no: int = 0
    reg_date: Optional[date] = None
    first_name: str = ""
    last_name: Optional[str] = None
    mother_name: Optional[str] = None  # Όνομα Μητρός
    national_id: Optional[str] = None
    birth_date: Optional[date] = None
    profession: Optional[str] = None
    married: bool = False
    marriage_date: Optional[date] = None
    is_active: bool = True
    is_deceased: bool = False  # Αποθανών/ούσα
    is_disabled: bool = False  # ΑΜΕΑ
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def validate(self) -> List[str]:
        """
        Validate required fields.
        
        Returns:
            List[str]: List of validation error messages. Empty list if valid.
        """
        errors = []
        
        # Required field validation
        if not self.first_name or not self.first_name.strip():
            errors.append("First name is required")
        
        if self.family_id <= 0:
            errors.append("Family ID is required")
        
        return errors
