# -*- coding: utf-8 -*-
"""
Payments repository for managing payment records.
"""

import logging
from services.audit_context import log_audit
from typing import List, Optional, Dict, Any
from db.connection import DatabaseConnection
from db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class PaymentsRepository(BaseRepository):
    """Repository for payments table operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        """Initialize PaymentsRepository."""
        super().__init__(db_connection, 'payments')
        self.reporting_service = None  # Will be set by dependency injection
        logger.debug("PaymentsRepository initialized")
    
    def get_by_legacy_pcode_and_family(self, legacy_pcode: int, family_id: int) -> Optional[Dict[str, Any]]:
        """
        Find a payment by legacy_pcode and family_id.
        Used during import to check if payment already exists.
        
        Args:
            legacy_pcode: Legacy PCODE from report.csv
            family_id: Family ID
            
        Returns:
            Payment record or None if not found
        """
        query = "SELECT * FROM payments WHERE legacy_pcode = %s AND family_id = %s"
        
        try:
            results = self.db.execute_query(query, (legacy_pcode, family_id))
            if results:
                logger.debug(f"Found payment with legacy_pcode={legacy_pcode}, family_id={family_id}")
                return results[0]
            return None
        except Exception as e:
            logger.error(f"Error finding payment by legacy_pcode and family: {e}")
            raise
    
    def list_payments(
        self,
        year: Optional[int] = None,
        family_id: Optional[int] = None,
        only_with_debt: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List payments with optional filters.
        
        Args:
            year: Filter by payment year
            family_id: Filter by family ID
            only_with_debt: If True, only return payments with remaining_amount > 0
            limit: Maximum number of records
            offset: Number of records to skip
            
        Returns:
            List of payment records with family info
        """
        where_clauses = []
        params = []
        
        if year is not None:
            where_clauses.append("p.year = %s")
            params.append(year)
        
        if family_id is not None:
            where_clauses.append("p.family_id = %s")
            params.append(family_id)
        
        if only_with_debt:
            where_clauses.append("p.remaining_amount > 0")
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
            SELECT p.*, 
                   f.last_name, f.first_name,
                   f.legacy_code as family_code,
                   CONCAT(f.last_name, ' ', f.first_name) as family_name
            FROM payments p
            LEFT JOIN families f ON p.family_id = f.id
            WHERE {where_clause}
            ORDER BY p.payment_date DESC, p.id DESC
            LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        
        try:
            results = self.db.execute_query(query, tuple(params))
            logger.debug(f"list_payments returned {len(results)} payments")
            return results
        except Exception as e:
            logger.error(f"Error listing payments: {e}")
            raise
    
    def count_payments(
        self,
        year: Optional[int] = None,
        family_id: Optional[int] = None,
        only_with_debt: bool = False
    ) -> int:
        """Count payments matching filters."""
        where_clauses = []
        params = []
        
        if year is not None:
            where_clauses.append("year = %s")
            params.append(year)
        
        if family_id is not None:
            where_clauses.append("family_id = %s")
            params.append(family_id)
        
        if only_with_debt:
            where_clauses.append("remaining_amount > 0")
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        query = f"SELECT COUNT(*) as count FROM payments WHERE {where_clause}"
        
        try:
            results = self.db.execute_query(query, tuple(params) if params else None)
            count = results[0]['count'] if results else 0
            logger.debug(f"count_payments returned {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting payments: {e}")
            raise
    
    def create_payment(self, payment_data: Dict[str, Any]) -> int:
        """
        Create a new payment record.
        
        Business Rule: Subscriptions require either paid_amount > 0 OR total_amount > 0
        Exception: Free subscriptions for association members are allowed with 0 amount
        """
        # Validate subscription rule
        has_subscription = (
            payment_data.get('subscription_start_date') is not None or
            payment_data.get('subscription_end_date') is not None
        )
        
        # Check if this is a free subscription (for association members)
        is_free_subscription = payment_data.get('is_free_subscription', False)
        
        if has_subscription and not is_free_subscription:
            paid_amount = payment_data.get('paid_amount', 0)
            total_amount = payment_data.get('total_amount', 0)
            
            # Allow subscription if either paid_amount OR total_amount is > 0
            if paid_amount == 0 and total_amount == 0:
                raise ValueError(
                    "Δεν μπορείτε να δημιουργήσετε συνδρομή χωρίς ποσό. "
                    "Το συνολικό ποσό ή το πληρωμένο ποσό πρέπει να είναι μεγαλύτερο από 0."
                )
        
        # Remove is_free_subscription from payment_data as it's not a database field
        if 'is_free_subscription' in payment_data:
            del payment_data['is_free_subscription']
        
        fields = [
            'family_id', 'legacy_code', 'legacy_pcode', 'payment_date',
            'payment_time', 'description', 'receipt_no', 'remarks',
            'total_amount', 'paid_amount', 'remaining_amount', 'status', 'year',
            'subscription_start_date', 'subscription_end_date', 'subscription_code',
            'support_package'
        ]
        
        insert_fields = [f for f in fields if f in payment_data]
        values = [payment_data[f] for f in insert_fields]
        
        fields_str = ', '.join(insert_fields)
        placeholders = ', '.join(['%s'] * len(insert_fields))
        
        query = f"INSERT INTO payments ({fields_str}) VALUES ({placeholders})"
        
        try:
            payment_id = self.db.execute_update(query, tuple(values))
            
            # Commit the payment first
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Created payment with id={payment_id}")
            log_audit(self.db, 'payments', payment_id, 'INSERT', None, payment_data)
            
            # If support_package is specified, update the client's support plan
            support_package = payment_data.get('support_package')
            if support_package and payment_data.get('family_id'):
                try:
                    from db.repositories.clients_repo import ClientsRepository
                    clients_repo = ClientsRepository(self.db)
                    
                    # Update client's support_plan
                    clients_repo.update_client(
                        payment_data['family_id'],
                        {'support_plan': support_package}
                    )
                    logger.info(f"Updated client {payment_data['family_id']} support_plan to {support_package}")
                except Exception as client_error:
                    logger.error(f"Error updating client support plan: {client_error}")
                    # Don't fail the payment creation if client update fails
            
            # If this is a subscription payment, create subscription record
            if has_subscription:
                try:
                    from db.repositories.subscriptions_repo import SubscriptionsRepository
                    subscriptions_repo = SubscriptionsRepository(self.db)
                    
                    # Prepare payment data with ID for subscription creation
                    payment_with_id = payment_data.copy()
                    payment_with_id['id'] = payment_id
                    # Pass the is_free_subscription flag to subscriptions_repo
                    payment_with_id['is_free_subscription'] = is_free_subscription
                    
                    # Create subscription record
                    subscription_id = subscriptions_repo.create_subscription_from_payment(payment_with_id)
                    logger.info(f"Created subscription with id={subscription_id} for payment_id={payment_id}")
                    
                except Exception as sub_error:
                    logger.error(f"Error creating subscription for payment {payment_id}: {sub_error}", exc_info=True)
                    # Don't rollback the payment, just log the error
                    # The payment is valid even without the subscription record
            
            # Invalidate reporting cache
            if self.reporting_service:
                self.reporting_service.invalidate_cache()
            
            return payment_id
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            # Rollback on error
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise
    
    def update_payment(self, payment_id: int, payment_data: Dict[str, Any]) -> bool:
        """
        Update an existing payment record.
        
        Business Rule: Subscriptions require either paid_amount > 0 OR total_amount > 0
        """
        payment_data = {k: v for k, v in payment_data.items() if k != 'id'}
        
        if not payment_data:
            return False
        
        # Remove is_free_subscription from payment_data as it's not a database field
        is_free_subscription = payment_data.pop('is_free_subscription', False)
        
        # Validate subscription rule
        has_subscription = (
            payment_data.get('subscription_start_date') is not None or
            payment_data.get('subscription_end_date') is not None
        )
        
        if has_subscription and not is_free_subscription:
            # Get current payment data to check amounts
            current_payment = self.get_payment_by_id(payment_id)
            
            # Use new values if provided, otherwise use current values
            paid_amount = payment_data.get('paid_amount', current_payment.get('paid_amount', 0) if current_payment else 0)
            total_amount = payment_data.get('total_amount', current_payment.get('total_amount', 0) if current_payment else 0)
            
            # Allow subscription if either paid_amount OR total_amount is > 0
            if paid_amount == 0 and total_amount == 0:
                raise ValueError(
                    "Δεν μπορείτε να δημιουργήσετε συνδρομή χωρίς ποσό. "
                    "Το συνολικό ποσό ή το πληρωμένο ποσό πρέπει να είναι μεγαλύτερο από 0."
                )
        
        set_clauses = [f"{field} = %s" for field in payment_data.keys()]
        values = list(payment_data.values())
        values.append(payment_id)
        
        query = f"UPDATE payments SET {', '.join(set_clauses)} WHERE id = %s"
        
        try:
            # Get current payment data BEFORE update to avoid deadlock
            current_payment = self.get_payment_by_id(payment_id) if has_subscription else None
            
            # Update payment
            rows_affected = self.db.execute_update(query, tuple(values))
            
            # Commit the payment update
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Updated payment id={payment_id}")
            log_audit(self.db, 'payments', payment_id, 'UPDATE', current_payment, payment_data)
            
            # If support_package is specified, update the client's support plan
            support_package = payment_data.get('support_package')
            if support_package and rows_affected > 0:
                # Get family_id from current payment if not in update data
                family_id = payment_data.get('family_id')
                if not family_id and current_payment:
                    family_id = current_payment.get('family_id')
                
                if family_id:
                    try:
                        from db.repositories.clients_repo import ClientsRepository
                        clients_repo = ClientsRepository(self.db)
                        
                        # Update client's support_plan
                        clients_repo.update_client(
                            family_id,
                            {'support_plan': support_package}
                        )
                        logger.info(f"Updated client {family_id} support_plan to {support_package}")
                    except Exception as client_error:
                        logger.error(f"Error updating client support plan: {client_error}")
                        # Don't fail the payment update if client update fails
            
            # If this is a subscription payment, update or create subscription record
            # Do this AFTER committing the payment to avoid deadlock
            if has_subscription and rows_affected > 0 and current_payment:
                try:
                    from db.repositories.subscriptions_repo import SubscriptionsRepository
                    subscriptions_repo = SubscriptionsRepository(self.db)
                    
                    # Prepare updated payment data
                    updated_payment = current_payment.copy()
                    updated_payment.update(payment_data)
                    updated_payment['id'] = payment_id
                    
                    # Check if subscription already exists
                    year = updated_payment.get('year')
                    family_id = updated_payment.get('family_id')
                    
                    existing_subscription = subscriptions_repo.get_by_family_and_year(family_id, year)
                    
                    if existing_subscription:
                        # Update existing subscription amounts
                        update_query = """
                            UPDATE subscriptions 
                            SET total_amount = %s, 
                                paid_amount = %s, 
                                remaining_amount = %s,
                                start_date = %s,
                                end_date = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """
                        self.db.execute_update(update_query, (
                            updated_payment.get('total_amount', 0),
                            updated_payment.get('paid_amount', 0),
                            updated_payment.get('remaining_amount', 0),
                            updated_payment.get('subscription_start_date'),
                            updated_payment.get('subscription_end_date'),
                            existing_subscription['id']
                        ))
                        connection.commit()
                        logger.info(f"Updated subscription id={existing_subscription['id']} for payment_id={payment_id}")
                    else:
                        # Create new subscription
                        subscription_id = subscriptions_repo.create_subscription_from_payment(updated_payment)
                        logger.info(f"Created subscription with id={subscription_id} for payment_id={payment_id}")
                    
                except Exception as sub_error:
                    logger.error(f"Error updating/creating subscription for payment {payment_id}: {sub_error}", exc_info=True)
                    # Don't rollback the payment, just log the error
            
            # Invalidate reporting cache
            if self.reporting_service and rows_affected > 0:
                self.reporting_service.invalidate_cache()
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Error updating payment id={payment_id}: {e}")
            # Rollback on error
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise
    
    def delete_payment(self, payment_id: int) -> bool:
        """
        Delete a payment record (hard delete).
        If payment has a linked subscription, delete the subscription first.
        """
        try:
            # First, check if this payment has a linked subscription
            from db.repositories.subscriptions_repo import SubscriptionsRepository
            subscriptions_repo = SubscriptionsRepository(self.db)
            
            check_query = "SELECT id FROM subscriptions WHERE payment_id = %s"
            subscription_results = self.db.execute_query(check_query, (payment_id,))
            
            if subscription_results:
                subscription_id = subscription_results[0]['id']
                logger.info(f"Deleting linked subscription id={subscription_id} before deleting payment id={payment_id}")
                
                # Delete the subscription first (this removes the foreign key constraint)
                subscriptions_repo.delete_subscription(subscription_id)
            
            _old_pay = self.get_payment_by_id(payment_id)
            # Now delete the payment
            query = "DELETE FROM payments WHERE id = %s"
            rows_affected = self.db.execute_update(query, (payment_id,))
            
            # Commit the change
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(f"Deleted payment id={payment_id}")
            log_audit(self.db, 'payments', payment_id, 'DELETE', _old_pay, None)
            
            # Invalidate reporting cache
            if self.reporting_service and rows_affected > 0:
                self.reporting_service.invalidate_cache()
            
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Error deleting payment id={payment_id}: {e}")
            # Rollback on error
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise
    
    def get_payment_by_id(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """Get payment by ID."""
        query = "SELECT * FROM payments WHERE id = %s"
        
        try:
            results = self.db.execute_query(query, (payment_id,))
            if results:
                logger.debug(f"Found payment with id={payment_id}")
                return results[0]
            return None
        except Exception as e:
            logger.error(f"Error getting payment id={payment_id}: {e}")
            raise
    
    def get_payment_with_family(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """Get payment with family information."""
        query = """
            SELECT p.*, 
                   f.last_name, f.first_name, f.father_name, 
                   f.spouse_name, f.spouse_maiden_name,
                   f.is_divorced, f.spouse_deceased,
                   f.address, f.city,
                   f.postal_code, f.phone, f.email,
                   f.legacy_code as family_code,
                   f.national_id, f.afm, f.doy, f.company_name, f.profession,
                   CONCAT(f.last_name, ' ', f.first_name) as family_name
            FROM payments p
            LEFT JOIN families f ON p.family_id = f.id
            WHERE p.id = %s
        """
        
        try:
            results = self.db.execute_query(query, (payment_id,))
            if results:
                logger.debug(f"Found payment with id={payment_id}")
                return results[0]
            return None
        except Exception as e:
            logger.error(f"Error getting payment id={payment_id}: {e}")
            raise
    
    def set_document_info(self, payment_id: int, document_type: str, receipt_no: str, vat_rate, document_notes=None) -> bool:
        """Set issued document type, number and VAT snapshot on a payment.

        `document_notes` are optional technician comments about the work; when
        provided (not None) they are stored and printed on the PDF. Passing
        None leaves any existing note untouched.
        """
        try:
            if document_notes is None:
                self.db.execute_update(
                    "UPDATE payments SET document_type=%s, receipt_no=%s, vat_rate=%s WHERE id=%s",
                    (document_type, receipt_no, vat_rate, payment_id)
                )
            else:
                self.db.execute_update(
                    "UPDATE payments SET document_type=%s, receipt_no=%s, vat_rate=%s, document_notes=%s WHERE id=%s",
                    (document_type, receipt_no, vat_rate, document_notes, payment_id)
                )
            self.db.commit()
            log_audit(self.db, 'payments', payment_id, 'UPDATE', None, {'document_type': document_type, 'receipt_no': receipt_no, 'vat_rate': vat_rate})
            return True
        except Exception as e:
            logger.error(f"Failed to set document info for payment {payment_id}: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass
            return False

    def get_unpaid_by_year(self, year: int) -> List[Dict[str, Any]]:
        """
        Get families with unpaid or partially paid subscriptions for a specific year.
        
        Args:
            year: The year to check for unpaid subscriptions
            
        Returns:
            List of dictionaries containing family and payment information
        """
        query = """
            SELECT 
                f.id as family_id,
                f.legacy_code as family_code,
                CONCAT(f.last_name, ' ', f.first_name) as family_name,
                f.phone,
                f.mobile,
                f.email,
                f.city,
                f.members_count,
                COALESCE(p.total_amount, 0) as total_amount,
                COALESCE(p.paid_amount, 0) as paid_amount,
                COALESCE(p.remaining_amount, 0) as remaining_amount,
                COALESCE(p.payment_date, NULL) as last_payment_date,
                CASE 
                    WHEN p.id IS NULL THEN 'unpaid'
                    WHEN p.remaining_amount > 0 THEN 'partial'
                    ELSE 'paid'
                END as payment_status
            FROM families f
            LEFT JOIN payments p ON f.id = p.family_id AND YEAR(p.payment_date) = %s
            WHERE f.is_active = 1
                AND (p.id IS NULL OR p.remaining_amount > 0)
            ORDER BY f.last_name, f.first_name
        """
        
        try:
            results = self.db.execute_query(query, (year,))
            logger.debug(f"Found {len(results)} families with unpaid/partial payments for year {year}")
            return results
        except Exception as e:
            logger.error(f"Error getting unpaid families for year {year}: {e}")
            raise
