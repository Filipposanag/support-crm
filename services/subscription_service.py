# -*- coding: utf-8 -*-
"""
Subscription Service - Handles subscription-related operations.
"""

import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from db.repositories.payments_repo import PaymentsRepository
from db.repositories.families_repo import FamiliesRepository

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Service for subscription-related operations.
    Provides methods to find expiring subscriptions for manual email sending.
    
    Business Rule: Subscriptions can only be created with paid receipts.
    """
    
    def __init__(
        self,
        payments_repo: PaymentsRepository,
        families_repo: FamiliesRepository
    ):
        """
        Initialize SubscriptionService.
        
        Args:
            payments_repo: Payments repository instance
            families_repo: Families repository instance
        """
        self.payments_repo = payments_repo
        self.families_repo = families_repo
    
    def get_subscriptions_expiring_in(
        self,
        days: int,
        only_unpaid: bool = False
    ) -> List[Dict]:
        """
        Get subscriptions expiring within specified days.
        
        Args:
            days: Number of days before expiration
            only_unpaid: If True, only return subscriptions with remaining amount > 0
            
        Returns:
            List of subscription dictionaries with family and payment info
        """
        try:
            # Calculate date range
            today = datetime.now().date()
            expiry_date = today + timedelta(days=days)
            
            # Query subscriptions
            query = """
                SELECT 
                    p.id as payment_id,
                    p.family_id,
                    p.payment_date,
                    p.subscription_end_date,
                    p.description,
                    p.total_amount,
                    p.paid_amount,
                    p.remaining_amount,
                    p.status,
                    p.receipt_no,
                    f.legacy_code as family_code,
                    f.last_name,
                    f.first_name,
                    f.email,
                    f.phone
                FROM payments p
                INNER JOIN families f ON p.family_id = f.id
                WHERE p.subscription_end_date <= %s
                AND p.subscription_end_date >= %s
            """
            
            params = [expiry_date, today]
            
            # Add unpaid filter if requested
            if only_unpaid:
                query += " AND p.remaining_amount > 0"
            
            # Order by expiry date
            query += " ORDER BY p.subscription_end_date ASC, f.last_name ASC"
            
            results = self.payments_repo.db.execute_query(query, tuple(params))
            
            # Process results
            subscriptions = []
            for row in results:
                # Skip if no email
                if not row.get('email'):
                    continue
                
                subscription = {
                    'payment_id': row['payment_id'],
                    'family_id': row['family_id'],
                    'family_code': row['family_code'],
                    'family_name': f"{row['last_name']} {row['first_name']}",
                    'email': row['email'],
                    'phone': row['phone'],
                    'payment_date': row['payment_date'],
                    'expiry_date': row['subscription_end_date'],
                    'description': row['description'],
                    'total_amount': float(row['total_amount']),
                    'paid_amount': float(row['paid_amount']),
                    'remaining_amount': float(row['remaining_amount']),
                    'status': row['status'],
                    'receipt_no': row['receipt_no']
                }
                subscriptions.append(subscription)
            
            logger.info(f"Found {len(subscriptions)} subscriptions expiring in {days} days")
            return subscriptions
            
        except Exception as e:
            logger.error(f"Failed to get expiring subscriptions: {e}", exc_info=True)
            return []
    
    def start_subscription(
        self,
        payment_id: int,
        start_date: Optional[date] = None,
        duration_days: int = 365
    ) -> bool:
        """
        Start a subscription for a payment.
        
        Business Rule: Payment must be paid (status='PAID' or 'PARTIAL' with paid_amount > 0)
        
        Args:
            payment_id: ID of the payment to convert to subscription
            start_date: Subscription start date (defaults to payment date)
            duration_days: Subscription duration in days (default 365 = 1 year)
            
        Returns:
            True if subscription started successfully
            
        Raises:
            ValueError: If payment is not found or not paid
        """
        try:
            # Get payment
            payment = self.payments_repo.get_by_id(payment_id)
            
            if not payment:
                raise ValueError("Η απόδειξη δεν βρέθηκε.")
            
            # Validate payment status
            if payment.get('status') == 'UNPAID' or payment.get('paid_amount', 0) == 0:
                raise ValueError(
                    "Δεν μπορείτε να ξεκινήσετε συνδρομή χωρίς εξοφλημένη απόδειξη. "
                    "Η απόδειξη πρέπει να έχει καταβληθεί τουλάχιστον μερικώς."
                )
            
            # Calculate dates
            if start_date is None:
                start_date = payment.get('payment_date')
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
            end_date = start_date + timedelta(days=duration_days)
            
            # Update payment with subscription dates
            update_data = {
                'subscription_start_date': start_date,
                'subscription_end_date': end_date
            }
            
            success = self.payments_repo.update(payment_id, update_data)
            
            if success:
                logger.info(
                    f"Subscription started for payment {payment_id}: "
                    f"{start_date} to {end_date}"
                )
            
            return success
            
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Failed to start subscription: {e}", exc_info=True)
            raise ValueError(f"Σφάλμα κατά την έναρξη συνδρομής: {str(e)}")
    
    def get_family_payments_for_subscription(
        self,
        family_id: int,
        year: Optional[int] = None
    ) -> List[Dict]:
        """
        Get paid payments for a family that can be used for subscriptions.
        
        Args:
            family_id: Family ID
            year: Optional year filter
            
        Returns:
            List of payment dictionaries
        """
        try:
            query = """
                SELECT 
                    id,
                    payment_date,
                    receipt_no,
                    description,
                    total_amount,
                    paid_amount,
                    remaining_amount,
                    status,
                    subscription_start_date,
                    subscription_end_date
                FROM payments
                WHERE family_id = %s
                AND status IN ('PAID', 'PARTIAL')
                AND paid_amount > 0
            """
            
            params = [family_id]
            
            if year:
                query += " AND year = %s"
                params.append(year)
            
            query += " ORDER BY payment_date DESC"
            
            results = self.payments_repo.db.execute_query(query, tuple(params))
            
            payments = []
            for row in results:
                payment = {
                    'id': row['id'],
                    'payment_date': row['payment_date'],
                    'receipt_no': row['receipt_no'] or f"#{row['id']}",
                    'description': row['description'] or 'Πληρωμή',
                    'total_amount': float(row['total_amount']),
                    'paid_amount': float(row['paid_amount']),
                    'remaining_amount': float(row['remaining_amount']),
                    'status': row['status'],
                    'has_subscription': row['subscription_start_date'] is not None,
                    'subscription_start_date': row['subscription_start_date'],
                    'subscription_end_date': row['subscription_end_date']
                }
                payments.append(payment)
            
            return payments
            
        except Exception as e:
            logger.error(f"Failed to get family payments: {e}", exc_info=True)
            return []

