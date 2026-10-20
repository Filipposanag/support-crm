# -*- coding: utf-8 -*-
"""
License Service - License validation and management.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class LicenseService:
    """
    Service for license validation and management.
    Simple local validation without online activation.
    """
    
    @staticmethod
    def validate_and_activate(license_key: str) -> Tuple[bool, str, str]:
        """
        Validate license key and return activation info.
        
        Args:
            license_key: License key to validate
            
        Returns:
            Tuple of (is_valid, owner_name, error_message)
        """
        try:
            # Clean up the key
            key = license_key.strip().upper()
            
            if not key:
                return False, "", "Το κλειδί άδειας δεν μπορεί να είναι κενό."
            
            # All license keys must be validated online
            # No local/demo keys allowed
            return False, "", "Μη έγκυρο κλειδί άδειας. Παρακαλώ επικοινωνήστε με την υποστήριξη."
            
        except Exception as e:
            logger.error(f"License validation error: {e}")
            return False, "", f"Σφάλμα επικύρωσης: {str(e)}"
    
    @staticmethod
    def calculate_license_dates() -> Tuple[datetime, datetime]:
        """
        Calculate license start and end dates (1 year from today).
        
        Returns:
            Tuple of (start_date, end_date)
        """
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=365)
        return start_date, end_date
    
    @staticmethod
    def calculate_days_remaining(end_date) -> int:
        """
        Calculate days remaining until license expiration.
        
        Args:
            end_date: License expiration date (datetime.date or datetime)
            
        Returns:
            Days remaining (negative if expired)
        """
        try:
            if isinstance(end_date, datetime):
                end_date = end_date.date()
            
            today = datetime.now().date()
            delta = end_date - today
            return delta.days
        except Exception as e:
            logger.error(f"Error calculating days remaining: {e}")
            return -999
    
    @staticmethod
    def get_license_status_text(status: str, days_remaining: int) -> str:
        """
        Get human-readable license status text.
        
        Args:
            status: License status ('active', 'expired', 'none')
            days_remaining: Days remaining until expiration
            
        Returns:
            Status text in Greek
        """
        if status == 'none':
            return "Δεν έχει οριστεί άδεια"
        elif status == 'expired':
            return f"Έληξε (πριν {abs(days_remaining)} ημέρες)"
        elif status == 'active':
            if days_remaining <= 0:
                return "Έληξε σήμερα"
            elif days_remaining == 1:
                return "Λήγει αύριο"
            elif days_remaining <= 30:
                return f"Λήγει σε {days_remaining} ημέρες"
            else:
                return f"Ενεργή ({days_remaining} ημέρες)"
        else:
            return "Άγνωστη κατάσταση"
    
    @staticmethod
    def get_license_status_color(status: str, days_remaining: int) -> str:
        """
        Get color for license status display.
        
        Args:
            status: License status ('active', 'expired', 'none')
            days_remaining: Days remaining until expiration
            
        Returns:
            Color hex code
        """
        if status == 'none':
            return '#757575'  # Gray
        elif status == 'expired' or days_remaining <= 0:
            return '#d32f2f'  # Red
        elif days_remaining <= 30:
            return '#FF9800'  # Orange
        else:
            return '#4CAF50'  # Green
    
    @staticmethod
    def is_license_active(license_info: dict) -> bool:
        """
        Check if license is active and not expired.
        
        Args:
            license_info: License info dictionary from SettingsService
            
        Returns:
            True if license is active and not expired, False otherwise
        """
        try:
            if not license_info or license_info.get('status') != 'active':
                return False
            
            end_date = license_info.get('end_date')
            if not end_date:
                return False
            
            # Convert to date if string
            if isinstance(end_date, str):
                from datetime import datetime
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Check if expired
            days_remaining = LicenseService.calculate_days_remaining(end_date)
            return days_remaining >= 0
            
        except Exception as e:
            logger.error(f"Error checking license status: {e}")
            return False
