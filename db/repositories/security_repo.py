# -*- coding: utf-8 -*-
"""
Security Settings Repository.
Handles database operations for security configuration.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SecuritySettingsRepository:
    """Repository for security settings operations."""
    
    def __init__(self, db_connection):
        """Initialize repository with database connection."""
        self.db = db_connection
    
    def get_settings(self) -> Dict[str, Any]:
        """
        Get current security settings.
        
        Returns:
            Dictionary with all security settings
        """
        try:
            query = "SELECT * FROM security_settings WHERE id = 1"
            results = self.db.execute_query(query)
            
            if results:
                return dict(results[0])
            
            # Return defaults if no settings exist
            return self._get_defaults()
            
        except Exception as e:
            logger.error(f"Error getting security settings: {e}")
            return self._get_defaults()
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Get default security settings."""
        return {
            'brute_force_enabled': True,
            'max_failed_attempts': 5,
            'lockout_duration_minutes': 15,
            'password_min_length': 6,
            'password_require_uppercase': False,
            'password_require_lowercase': False,
            'password_require_number': False,
            'password_require_special': False,
            'session_duration_hours': 8,
            'bcrypt_rounds': 12
        }
    
    def update_settings(self, settings: Dict[str, Any], updated_by: int = None) -> bool:
        """
        Update security settings.
        
        Args:
            settings: Dictionary with settings to update
            updated_by: User ID who made the change
            
        Returns:
            True if successful
        """
        try:
            # Build update query dynamically
            allowed_fields = [
                'brute_force_enabled', 'max_failed_attempts', 'lockout_duration_minutes',
                'password_min_length', 'password_require_uppercase', 'password_require_lowercase',
                'password_require_number', 'password_require_special',
                'session_duration_hours', 'bcrypt_rounds'
            ]
            
            updates = []
            values = []
            
            for field in allowed_fields:
                if field in settings:
                    updates.append(f"{field} = %s")
                    values.append(settings[field])
            
            if not updates:
                return True
            
            # Add updated_by
            if updated_by:
                updates.append("updated_by = %s")
                values.append(updated_by)
            
            query = f"UPDATE security_settings SET {', '.join(updates)} WHERE id = 1"
            self.db.execute_update(query, tuple(values))
            self.db.commit()
            
            logger.info(f"Security settings updated by user {updated_by}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating security settings: {e}")
            return False
    
    def ensure_settings_exist(self) -> bool:
        """Ensure security settings row exists."""
        try:
            query = "INSERT IGNORE INTO security_settings (id) VALUES (1)"
            self.db.execute_update(query)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error ensuring security settings: {e}")
            return False
