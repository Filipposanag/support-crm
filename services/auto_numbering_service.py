# -*- coding: utf-8 -*-
"""
Auto-Numbering Service
Provides automatic sequential numbering for receipts, subscriptions, and families.
"""

import logging
from typing import Optional, Tuple
from db.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class AutoNumberingService:
    """
    Service for managing automatic sequential numbering.
    Handles receipts, subscriptions, and families with configurable prefixes and counters.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize AutoNumberingService.
        
        Args:
            db_connection: Database connection instance
        """
        self.db_connection = db_connection
    
    def get_next_receipt_number(self) -> str:
        """
        Get next receipt number and increment counter.
        
        Returns:
            Formatted receipt number (e.g., "ΑΠ-0001")
        """
        return self._get_next_number('receipt')
    
    def get_next_subscription_number(self) -> str:
        """
        Get next subscription number and increment counter.
        
        Returns:
            Formatted subscription number (e.g., "ΣΥΝ-0001")
        """
        return self._get_next_number('subscription')

    def get_next_invoice_number(self) -> str:
        """Get next invoice number (e.g. 'ΤΠΥ-0001') and increment counter."""
        return self._get_next_number('invoice')
    
    def get_next_legacy_code(self) -> int:
        """
        Get next legacy_code for a new family.
        
        Returns:
            Next available legacy_code as integer
        """
        try:
            # Find the maximum legacy_code in the database
            max_query = """
                SELECT MAX(legacy_code) as max_code
                FROM families
            """
            max_results = self.db_connection.execute_query(max_query)
            
            max_code = 0
            if max_results and max_results[0]['max_code']:
                max_code = int(max_results[0]['max_code'])
            
            # Return next code
            next_code = max_code + 1
            
            logger.info(f"Generated next legacy_code: {next_code}")
            return next_code
            
        except Exception as e:
            logger.error(f"Failed to generate legacy_code: {e}")
            return 1  # Fallback to 1
    
    def _get_next_number(self, number_type: str) -> str:
        """
        Get next number for specified type and increment counter.
        Automatically syncs with database to find the next available number.
        
        Args:
            number_type: Type of number ('receipt', 'subscription', 'family')
            
        Returns:
            Formatted number string
        """
        try:
            # Get current counter and prefix
            counter_field = f"{number_type}_counter"
            prefix_field = f"{number_type}_prefix"
            
            query = f"SELECT {counter_field}, {prefix_field} FROM app_settings WHERE id = 1"
            results = self.db_connection.execute_query(query)
            
            if not results:
                logger.error("No settings found in app_settings table")
                return f"ERROR-0001"
            
            current_counter = results[0][counter_field]
            prefix = results[0][prefix_field] or ''
            
            # Determine table and field based on type
            if number_type == 'receipt':
                table = 'payments'
                field = 'receipt_no'
            elif number_type == 'subscription':
                table = 'payments'
                field = 'subscription_code'
            elif number_type == 'invoice':
                table = 'payments'
                field = 'receipt_no'
            else:
                raise ValueError(f"Unknown number type: {number_type}")
            
            # Find the maximum number in the database
            max_query = f"""
                SELECT MAX(CAST(SUBSTRING_INDEX({field}, '-', -1) AS UNSIGNED)) as max_no
                FROM {table}
                WHERE {field} LIKE %s
            """
            max_results = self.db_connection.execute_query(max_query, (f"{prefix}-%",))
            
            max_no = 0
            if max_results and max_results[0]['max_no']:
                max_no = int(max_results[0]['max_no'])
            
            # Use the greater of current_counter or max_no + 1
            next_counter = max(current_counter, max_no + 1)
            
            # Format number with leading zeros (4 digits)
            formatted_number = f"{prefix}-{next_counter:04d}"
            
            # Update counter in database to next_counter + 1
            update_query = f"""
                UPDATE app_settings 
                SET {counter_field} = %s
                WHERE id = 1
            """
            self.db_connection.execute_update(update_query, (next_counter + 1,))
            
            # Commit the change
            connection = self.db_connection.get_connection()
            connection.commit()
            
            logger.info(f"Generated {number_type} number: {formatted_number} (synced from max: {max_no})")
            return formatted_number
            
        except Exception as e:
            logger.error(f"Failed to generate {number_type} number: {e}")
            try:
                connection = self.db_connection.get_connection()
                connection.rollback()
            except:
                pass
            return f"ERROR-{number_type[:3].upper()}"
    
    def check_number_exists(self, number: str, table: str, field: str) -> bool:
        """
        Check if a number already exists in the database.
        
        Args:
            number: Number to check
            table: Table name ('payments', 'families', etc.)
            field: Field name to check
            
        Returns:
            True if number exists, False otherwise
        """
        try:
            query = f"SELECT COUNT(*) as count FROM {table} WHERE {field} = %s"
            results = self.db_connection.execute_query(query, (number,))
            
            if results and results[0]['count'] > 0:
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to check number existence: {e}")
            return False
    
    def get_numbering_config(self) -> dict:
        """
        Get current numbering configuration.
        
        Returns:
            Dictionary with counters and prefixes
        """
        try:
            query = """
                SELECT 
                    receipt_counter, receipt_prefix,
                    subscription_counter, subscription_prefix
                FROM app_settings WHERE id = 1
            """
            results = self.db_connection.execute_query(query)
            
            if results:
                return {
                    'receipt_counter': results[0]['receipt_counter'],
                    'receipt_prefix': results[0]['receipt_prefix'],
                    'subscription_counter': results[0]['subscription_counter'],
                    'subscription_prefix': results[0]['subscription_prefix']
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get numbering config: {e}")
            return {}
    
    def update_numbering_config(self, config: dict) -> bool:
        """
        Update numbering configuration.
        
        Args:
            config: Dictionary with counters and prefixes to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build update query dynamically based on provided config
            updates = []
            values = []
            
            for key, value in config.items():
                if key in ['receipt_counter', 'receipt_prefix', 
                          'subscription_counter', 'subscription_prefix']:
                    updates.append(f"{key} = %s")
                    values.append(value)
            
            if not updates:
                logger.warning("No valid config fields to update")
                return False
            
            query = f"""
                UPDATE app_settings 
                SET {', '.join(updates)}
                WHERE id = 1
            """
            
            self.db_connection.execute_update(query, tuple(values))
            self.db_connection.commit()
            
            logger.info(f"Updated numbering config: {config}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update numbering config: {e}")
            self.db_connection.rollback()
            return False
    
    def reset_counter(self, number_type: str, start_value: int = 1) -> bool:
        """
        Reset counter to specified value.
        
        Args:
            number_type: Type of counter ('receipt', 'subscription')
            start_value: Starting value for counter
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if number_type not in ['receipt', 'subscription']:
                logger.error(f"Invalid counter type: {number_type}")
                return False
            
            counter_field = f"{number_type}_counter"
            
            query = f"""
                UPDATE app_settings 
                SET {counter_field} = %s
                WHERE id = 1
            """
            
            self.db_connection.execute_update(query, (start_value,))
            self.db_connection.commit()
            
            logger.info(f"Reset {number_type} counter to {start_value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset {number_type} counter: {e}")
            self.db_connection.rollback()
            return False
