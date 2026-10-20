# -*- coding: utf-8 -*-
"""
Subscriptions repository for managing subscription records.
"""

import logging
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from db.connection import DatabaseConnection
from db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class SubscriptionsRepository(BaseRepository):
    """Repository for subscriptions table operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        """Initialize SubscriptionsRepository."""
        super().__init__(db_connection, 'subscriptions')
        logger.debug("SubscriptionsRepository initialized")
    
    def create_subscription_from_payment(self, payment: dict) -> int:
        """
        Δημιουργεί συνδρομή με βάση μια πληρωμή.
        
        - Χρησιμοποιεί το family_id της απόδειξης
        - Χρησιμοποιεί τα subscription_start_date και subscription_end_date από την πληρωμή
        - Υπολογίζει το έτος συνδρομής από το year field ή από το subscription_start_date
        - Συνδέει την συνδρομή με το payment_id
        
        Args:
            payment: Dictionary containing payment data
            
        Returns:
            int: The ID of the newly created subscription
            
        Raises:
            ValueError: If payment data is invalid
            Exception: If database operation fails
        """
        try:
            # Extract payment data
            family_id = payment.get("family_id")
            payment_id = payment.get("id")
            
            # Validate required fields
            if not family_id:
                raise ValueError("family_id is required")
            if not payment_id:
                raise ValueError("payment_id is required")
            
            # Validate business rule: Subscription requires either paid_amount OR total_amount > 0
            # Exception: Free subscriptions for association members are allowed with 0 amount
            paid_amount_val = payment.get("paid_amount", 0)
            total_amount_val = payment.get("total_amount", 0)
            is_free_subscription = payment.get("is_free_subscription", False)
            
            if paid_amount_val == 0 and total_amount_val == 0 and not is_free_subscription:
                raise ValueError(
                    "Δεν μπορείτε να δημιουργήσετε συνδρομή χωρίς ποσό. "
                    "Το συνολικό ποσό ή το πληρωμένο ποσό πρέπει να είναι μεγαλύτερο από 0."
                )
            
            # Get subscription dates from payment
            start_date = payment.get("subscription_start_date")
            end_date = payment.get("subscription_end_date")
            
            # Validate subscription dates
            # Note: end_date can be None for free subscriptions (no expiry)
            if not start_date:
                raise ValueError("subscription_start_date is required")
            if not end_date and not is_free_subscription:
                raise ValueError("subscription_end_date is required for paid subscriptions")
            
            # Convert dates to date objects if they're strings
            if isinstance(start_date, str):
                try:
                    start_date = date.fromisoformat(start_date)
                except ValueError:
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
            # end_date can be None for free subscriptions
            if end_date is not None and isinstance(end_date, str):
                try:
                    end_date = date.fromisoformat(end_date)
                except ValueError:
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Calculate subscription year from year field or start_date
            subscription_year = payment.get("year")
            if not subscription_year:
                subscription_year = start_date.year
            
            # Extract amounts from payment
            total_amount = payment.get("total_amount", 0)
            paid_amount = payment.get("paid_amount", 0)
            remaining_amount = payment.get("remaining_amount", 0)
            
            # Extract subscription_code from payment
            subscription_code = payment.get("subscription_code")
            
            # SQL query
            sql = """
                INSERT INTO subscriptions (
                    family_id,
                    year,
                    start_date,
                    end_date,
                    status,
                    payment_id,
                    subscription_code,
                    total_amount,
                    paid_amount,
                    remaining_amount,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            # Check if subscription already exists for this family and year
            check_sql = """
                SELECT id, payment_id FROM subscriptions 
                WHERE family_id = %s AND year = %s
            """
            existing = self.db.execute_query(check_sql, (family_id, subscription_year))
            
            if existing and len(existing) > 0:
                existing_id = existing[0]['id']
                existing_payment_id = existing[0]['payment_id']
                
                # If this is the SAME payment being updated, REPLACE the amounts
                if existing_payment_id == payment_id:
                    logger.info(f"Subscription already exists (id={existing_id}) for same payment_id={payment_id} - replacing amounts")
                    
                    update_sql = """
                        UPDATE subscriptions
                        SET total_amount = %s,
                            paid_amount = %s,
                            remaining_amount = %s,
                            start_date = %s,
                            end_date = %s,
                            subscription_code = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """
                    self.db.execute_update(update_sql, (total_amount, paid_amount, remaining_amount, start_date, end_date, subscription_code, existing_id))
                    connection = self.db.get_connection()
                    connection.commit()
                    
                    logger.info(f"Replaced amounts in subscription id={existing_id}")
                    return existing_id
                else:
                    # Different payment - this is an ADDITIONAL payment for the same year
                    # ADD the amounts (e.g., family paid twice for the same year)
                    logger.info(f"Subscription already exists (id={existing_id}) for different payment - adding amounts")
                    
                    update_sql = """
                        UPDATE subscriptions
                        SET total_amount = total_amount + %s,
                            paid_amount = paid_amount + %s,
                            remaining_amount = remaining_amount + %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """
                    self.db.execute_update(update_sql, (total_amount, paid_amount, remaining_amount, existing_id))
                    connection = self.db.get_connection()
                    connection.commit()
                    
                    logger.info(f"Added amounts to existing subscription id={existing_id}")
                    return existing_id
            
            params = (
                family_id,
                subscription_year,
                start_date,
                end_date,
                "ACTIVE",
                payment_id,
                subscription_code,
                total_amount,
                paid_amount,
                remaining_amount
            )
            
            # Execute insert
            new_id = self.db.execute_update(sql, params)
            
            # Commit the transaction
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(
                f"Created subscription id={new_id} for family_id={family_id}, "
                f"year={subscription_year}, payment_id={payment_id}"
            )
            
            return new_id
            
        except ValueError as e:
            logger.error(f"Validation error creating subscription: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating subscription from payment: {e}", exc_info=True)
            # Rollback on error
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise
    
    def get_by_family_and_year(self, family_id: int, year: int) -> Optional[Dict[str, Any]]:
        """
        Get subscription for a specific family and year.
        
        Args:
            family_id: Family ID
            year: Subscription year
            
        Returns:
            Subscription dictionary or None if not found
        """
        try:
            query = """
                SELECT s.*, 
                       f.last_name, f.first_name,
                       p.receipt_no, p.payment_date
                FROM subscriptions s
                LEFT JOIN families f ON s.family_id = f.id
                LEFT JOIN payments p ON s.payment_id = p.id
                WHERE s.family_id = %s AND s.year = %s
            """
            
            results = self.db.execute_query(query, (family_id, year))
            
            if results:
                return results[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting subscription: {e}")
            return None
    
    def get_latest_subscription_by_family(self, family_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the latest subscription for a family (by end_date).
        
        Args:
            family_id: Family ID
            
        Returns:
            Latest subscription dictionary or None if not found
        """
        try:
            query = """
                SELECT s.*, 
                       f.last_name, f.first_name,
                       p.receipt_no, p.payment_date
                FROM subscriptions s
                LEFT JOIN families f ON s.family_id = f.id
                LEFT JOIN payments p ON s.payment_id = p.id
                WHERE s.family_id = %s
                ORDER BY s.end_date DESC, s.id DESC
                LIMIT 1
            """
            
            results = self.db.execute_query(query, (family_id,))
            
            if results:
                return results[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest subscription for family {family_id}: {e}")
            return None
    
    def list_by_family(self, family_id: int) -> List[Dict[str, Any]]:
        """
        List all subscriptions for a family.
        
        Args:
            family_id: Family ID
            
        Returns:
            List of subscription dictionaries
        """
        try:
            query = """
                SELECT s.*, 
                       f.last_name, f.first_name,
                       p.receipt_no, p.payment_date
                FROM subscriptions s
                LEFT JOIN families f ON s.family_id = f.id
                LEFT JOIN payments p ON s.payment_id = p.id
                WHERE s.family_id = %s
                ORDER BY s.year DESC
            """
            
            results = self.db.execute_query(query, (family_id,))
            return results
            
        except Exception as e:
            logger.error(f"Error listing subscriptions for family {family_id}: {e}")
            return []
    
    def list_active_subscriptions(self) -> List[Dict[str, Any]]:
        """
        List all active subscriptions.
        
        Returns:
            List of active subscription dictionaries
        """
        try:
            query = """
                SELECT s.*, 
                       f.last_name, f.first_name, f.email, f.phone,
                       p.receipt_no, p.payment_date
                FROM subscriptions s
                LEFT JOIN families f ON s.family_id = f.id
                LEFT JOIN payments p ON s.payment_id = p.id
                WHERE s.status = 'ACTIVE'
                ORDER BY s.end_date ASC, f.last_name ASC
            """
            
            results = self.db.execute_query(query)
            return results
            
        except Exception as e:
            logger.error(f"Error listing active subscriptions: {e}")
            return []
    
    def update_status(self, subscription_id: int, status: str) -> bool:
        """
        Update subscription status.
        
        Args:
            subscription_id: Subscription ID
            status: New status (ACTIVE, EXPIRED, CANCELLED)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = "UPDATE subscriptions SET status = %s, updated_at = NOW() WHERE id = %s"
            rows_affected = self.db.execute_update(query, (status, subscription_id))
            
            # Commit the change
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Updated subscription {subscription_id} status to {status}")
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Error updating subscription status: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            return False
    
    def cancel_subscription(self, subscription_id: int, cancel_date: date, reason: str = None) -> bool:
        """
        Cancel a subscription by setting its status to CANCELLED.
        
        Args:
            subscription_id: Subscription ID
            cancel_date: Date of cancellation
            reason: Optional reason for cancellation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
                UPDATE subscriptions 
                SET status = %s,
                    end_date = %s,
                    updated_at = NOW()
                WHERE id = %s
            """
            params = ("CANCELLED", cancel_date, subscription_id)
            rows_affected = self.db.execute_update(query, params)
            
            # Commit the change
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Cancelled subscription {subscription_id} on {cancel_date}, reason: {reason or 'N/A'}")
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Error cancelling subscription: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            return False
    
    def delete_subscription(self, subscription_id: int) -> bool:
        """
        Delete a subscription record.
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = "DELETE FROM subscriptions WHERE id = %s"
            rows_affected = self.db.execute_update(query, (subscription_id,))
            
            # Commit the change
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Deleted subscription {subscription_id}")
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Error deleting subscription: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            return False

