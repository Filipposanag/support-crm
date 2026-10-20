# -*- coding: utf-8 -*-
"""
Session Service for Support CRM.
Handles support session tracking, timing, and automatic billing.
"""

import logging
from services.audit_context import log_audit
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
import math

from db.connection import DatabaseConnection
from models.client import SupportSession


logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing support sessions and billing."""
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize session service.
        
        Args:
            db_connection: Database connection instance
        """
        self.db = db_connection
        self.rounding_minutes = 0  # Disabled: count exact minutes (was 15)
    
    def start_session(
        self,
        client_id: int,
        session_type: str = 'remote',
        technician: str = '',
        description: str = '',
        rustdesk_session_id: str = ''
    ) -> Optional[int]:
        """
        Start a new support session.
        
        Args:
            client_id: Client ID
            session_type: Type of session (remote, onsite, phone, email)
            technician: Name of technician/support person
            description: Session description
            rustdesk_session_id: RustDesk session identifier (if applicable)
            
        Returns:
            Session ID if created successfully, None otherwise
        """
        try:
            query = """
                INSERT INTO support_sessions (
                    client_id, session_type, start_time, 
                    technician, rustdesk_session_id, description, status
                ) VALUES (%s, %s, %s, %s, %s, %s, 'active')
            """
            
            now = datetime.now()
            
            session_id = self.db.execute_update(query, (
                client_id,
                session_type,
                now,  # Full datetime
                technician,
                rustdesk_session_id,
                description
            ))
            
            connection = self.db.get_connection()
            connection.commit()
                
            logger.info(f"Started session {session_id} for client {client_id}")
            log_audit(self.db, 'support_sessions', session_id, 'INSERT', None,
                      {'client_id': client_id, 'session_type': session_type,
                       'technician': technician, 'description': description})
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            return None
    
    def end_session(
        self,
        session_id: int,
        issue_summary: str = '',
        auto_bill: bool = True
    ) -> bool:
        """
        End an active support session and optionally create billing.
        
        Args:
            session_id: Session ID to end
            issue_summary: Summary of issue resolved
            auto_bill: Automatically create payment record
            
        Returns:
            True if session ended successfully, False otherwise
        """
        try:
            # Get session details
            session = self.get_session(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False
            
            if session.status != 'active':
                logger.warning(f"Session {session_id} is not active")
                return False
            
            # Calculate duration
            end_time = datetime.now()
            start_time = session.start_time
            
            # Calculate exact duration in seconds
            duration_seconds = int((end_time - start_time).total_seconds())
            
            # Calculate minutes (ceiling for billing)
            duration_minutes = math.ceil(duration_seconds / 60)
            
            # Round duration if configured (e.g., to nearest 15 minutes)
            if self.rounding_minutes > 0:
                duration_minutes = self._round_duration(duration_minutes)
            
            # Package-aware billing with SPLIT overflow (decided here, at session end):
            #  - subscription client: fully covered, no per-session charge.
            #  - package client: deduct available package hours; any time BEYOND the
            #    available hours is charged hourly (each started hour = full rate) and
            #    recorded as a DEBT in Οφειλές.
            #  - no package/subscription: the whole session is charged hourly (DEBT).
            is_subscription = self._is_subscription_client(session.client_id)
            avail_hours = (Decimal('0.00') if is_subscription
                           else self._available_package_hours(session.client_id))
            has_package = avail_hours > Decimal('0')
            billed_amount = Decimal('0.00')
            charged_seconds = 0  # χρόνος που όντως χρεώνεται (υπέρβαση ή όλη η συνεδρία)
            if auto_bill and not is_subscription:
                if has_package:
                    covered_seconds = int(avail_hours * Decimal('3600'))
                    overflow_seconds = max(0, duration_seconds - covered_seconds)
                    charged_seconds = overflow_seconds
                    if overflow_seconds > 0:
                        billed_amount = self._hourly_charge(session.client_id, overflow_seconds)
                else:
                    charged_seconds = duration_seconds
                    billed_amount = self._hourly_charge(session.client_id, duration_seconds)
            
            # Update session
            query = """
                UPDATE support_sessions
                SET end_time = %s,
                    duration_seconds = %s,
                    duration_minutes = %s,
                    issue_summary = %s,
                    status = 'completed',
                    billed_amount = %s
                WHERE id = %s
            """
            
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(query, (
                    end_time,
                    duration_seconds,
                    duration_minutes,
                    issue_summary,
                    billed_amount,
                    session_id
                ))
                connection.commit()
            
            logger.info(f"Ended session {session_id}: {duration_minutes} minutes, billed {billed_amount}")
            log_audit(self.db, 'support_sessions', session_id, 'UPDATE', None,
                      {'status': 'completed', 'duration_minutes': duration_minutes,
                       'billed_amount': str(billed_amount)})
            
            # Client has a package -> cover the session by deducting hours.
            if has_package:
                self._deduct_prepaid_hours(session.client_id, duration_minutes)

            # No package -> the hourly charge becomes an outstanding debt.
            if auto_bill and billed_amount > 0:
                _charged_min = max(1, math.ceil(charged_seconds / 60)) if charged_seconds else 0
                if has_package:
                    _desc = f"Υπέρβαση πακέτου — συνεδρία #{session_id}: {_charged_min}′ εκτός πακέτου"
                else:
                    _desc = f"Χρέωση συνεδρίας #{session_id} (ωριαία)"
                self._create_payment_from_session(
                    session_id, session.client_id, billed_amount, _desc,
                    remarks=f"billed_minutes={_charged_min}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            connection = self.db.get_connection()
            connection.rollback()
            return False
    
    def cancel_session(self, session_id: int, reason: str = '') -> bool:
        """
        Cancel an active session without billing.
        
        Args:
            session_id: Session ID to cancel
            reason: Cancellation reason
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            query = """
                UPDATE support_sessions
                SET status = 'cancelled',
                    end_time = %s,
                    issue_summary = %s
                WHERE id = %s AND status = 'active'
            """
            
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(query, (datetime.now(), f"Cancelled: {reason}", session_id))
                affected = cursor.rowcount
                connection.commit()
            
            if affected > 0:
                logger.info(f"Cancelled session {session_id}")
                return True
            else:
                logger.warning(f"Session {session_id} not found or not active")
                return False
                
        except Exception as e:
            logger.error(f"Failed to cancel session: {e}")
            connection = self.db.get_connection()
            connection.rollback()
            return False
            self.db.connection.rollback()
            return False
    
    def get_session(self, session_id: int) -> Optional[SupportSession]:
        """
        Get session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            SupportSession object or None if not found
        """
        try:
            query = """
                SELECT id, client_id, session_type, start_time, end_time,
                       duration_minutes, rustdesk_session_id, technician,
                       description, issue_summary, status, billed_amount, payment_id
                FROM support_sessions
                WHERE id = %s
            """
            
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(query, (session_id,))
                row = cursor.fetchone()
                
                if row:
                    return SupportSession(
                        id=row['id'],
                        client_id=row['client_id'],
                        session_type=row['session_type'],
                        start_time=row['start_time'],
                        end_time=row['end_time'],
                        duration_minutes=row['duration_minutes'] or 0,
                        duration_seconds=row.get('duration_seconds') or 0,
                        rustdesk_session_id=row.get('rustdesk_session_id') or '',
                        technician=row['technician'],
                        description=row['description'],
                        issue_summary=row['issue_summary'],
                        status=row['status'],
                        billed_amount=row['billed_amount'],
                        payment_id=row['payment_id']
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all active sessions.
        
        Returns:
            List of active session dictionaries
        """
        try:
            query = """
                SELECT id, client_id, session_type, start_time, end_time,
                       duration_minutes, description, issue_summary, 
                       status, billed_amount, payment_id
                FROM support_sessions
                WHERE status = 'active'
                ORDER BY start_time DESC
            """
            
            results = self.db.execute_query(query)
            return results if results else []
            
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
    
    def get_client_sessions(
        self,
        client_id: int,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[SupportSession]:
        """
        Get sessions for a specific client.
        
        Args:
            client_id: Client ID
            limit: Maximum number of sessions to return
            status: Filter by status (active, completed, cancelled) or None for all
            
        Returns:
            List of SupportSession objects
        """
        try:
            query = """
                SELECT id, client_id, session_type, start_time, end_time,
                       duration_minutes, rustdesk_session_id, technician,
                       description, issue_summary, status, billed_amount, payment_id
                FROM support_sessions
                WHERE client_id = %s
            """
            params = [client_id]
            
            if status:
                query += " AND status = %s"
                params.append(status)
            
            query += " ORDER BY start_time DESC LIMIT %s"
            params.append(limit)
            
            sessions = []
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                for row in cursor.fetchall():
                    sessions.append(SupportSession(
                        id=row['id'],
                        client_id=row['client_id'],
                        session_type=row['session_type'],
                        start_time=row['start_time'],
                        end_time=row['end_time'],
                        duration_minutes=row['duration_minutes'],
                        rustdesk_session_id=row['rustdesk_session_id'],
                        technician=row['technician'],
                        description=row['description'],
                        issue_summary=row['issue_summary'],
                        status=row['status'],
                        billed_amount=row['billed_amount'],
                        payment_id=row['payment_id']
                    ))
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get client sessions: {e}")
            return []
    
    def _round_duration(self, minutes: int) -> int:
        """
        Round duration to nearest interval.
        
        Args:
            minutes: Duration in minutes
            
        Returns:
            Rounded duration
        """
        if self.rounding_minutes <= 0:
            return minutes
        
        return int(math.ceil(minutes / self.rounding_minutes) * self.rounding_minutes)
    
    def _get_default_hourly_rate(self) -> Decimal:
        """Read the global default hourly rate from app_settings (fallback 50.00 EUR)."""
        try:
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT default_hourly_rate FROM app_settings WHERE id = 1")
                row = cursor.fetchone()
                if row:
                    rate = row.get('default_hourly_rate') if isinstance(row, dict) else row[0]
                    if rate is not None and Decimal(str(rate)) > Decimal('0.00'):
                        return Decimal(str(rate))
        except Exception as e:
            logger.warning(f"Could not read default_hourly_rate, using 40.00: {e}")
        return Decimal('40.00')

    def _has_active_package_hours(self, client_id: int) -> bool:
        """True if the client has any active, non-expired package with remaining hours."""
        try:
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM client_package_hours "
                    "WHERE client_id = %s AND is_active = 1 "
                    "AND (expiry_date IS NULL OR expiry_date >= CURDATE()) "
                    "AND remaining_hours > 0 LIMIT 1", (client_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check package hours: {e}")
            return False

    def _available_package_hours(self, client_id: int) -> Decimal:
        """Σύνολο διαθέσιμων ωρών σε ενεργά, μη-ληγμένα πακέτα (Decimal). 0 αν κανένα."""
        try:
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COALESCE(SUM(remaining_hours),0) AS rh FROM client_package_hours "
                    "WHERE client_id = %s AND is_active = 1 "
                    "AND (expiry_date IS NULL OR expiry_date >= CURDATE()) "
                    "AND remaining_hours > 0", (client_id,))
                row = cursor.fetchone()
            rh = (row.get('rh') if isinstance(row, dict) else (row[0] if row else 0))
            return Decimal(str(rh or 0))
        except Exception as e:
            logger.error(f"Failed to sum package hours: {e}")
            return Decimal('0.00')

    def _is_subscription_client(self, client_id: int) -> bool:
        """True if the client is on a monthly/yearly subscription plan
        (prepaid coverage -> sessions are not charged per-session)."""
        try:
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT support_plan FROM families WHERE id = %s", (client_id,))
                row = cursor.fetchone()
            if row:
                plan = row.get('support_plan') if isinstance(row, dict) else row[0]
                return str(plan or '').lower() in ('monthly', 'yearly')
        except Exception as e:
            logger.error(f"Subscription check failed: {e}")
        return False

    def _hourly_charge(self, client_id: int, duration_seconds: int) -> Decimal:
        """Block hourly charge (no package): each STARTED hour costs the full rate.
        1 second-60:00 -> 1 block; 60:01-120:00 -> 2 blocks; etc."""
        try:
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT hourly_rate FROM families WHERE id = %s", (client_id,))
                row = cursor.fetchone()
            rate = Decimal('0.00')
            if row:
                hr = row.get('hourly_rate') if isinstance(row, dict) else row[0]
                if hr is not None:
                    rate = Decimal(str(hr))
            if rate <= Decimal('0.00'):
                rate = self._get_default_hourly_rate()
            secs = int(duration_seconds or 0)
            if secs <= 0:
                return Decimal('0.00')
            blocks = math.ceil(secs / 3600)
            return (Decimal(blocks) * rate).quantize(Decimal('0.01'))
        except Exception as e:
            logger.error(f"Failed to compute hourly charge: {e}")
            return Decimal('0.00')

    def _calculate_billing(self, client_id: int, duration_minutes: int) -> Decimal:
        """
        Calculate billing amount based on client's support plan.
        
        Args:
            client_id: Client ID
            duration_minutes: Session duration in minutes
            
        Returns:
            Billing amount
        """
        try:
            # Get client's support plan and rates
            query = """
                SELECT support_plan, hourly_rate, monthly_rate
                FROM families
                WHERE id = %s
            """
            
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(query, (client_id,))
                row = cursor.fetchone()
                
                if not row:
                    logger.warning(f"Client {client_id} not found")
                    return Decimal('0.00')
                
                support_plan = row['support_plan']
                hourly_rate = row.get('hourly_rate') or Decimal('0.00')
                monthly_rate = row.get('monthly_rate') or Decimal('0.00')

                # Effective hourly rate: use the client's own rate if set,
                # otherwise fall back to the global default_hourly_rate
                # (app_settings). This makes per-session hourly billing work
                # even when no per-client rate has been entered.
                effective_hourly_rate = Decimal(str(hourly_rate))
                if effective_hourly_rate <= Decimal('0.00'):
                    effective_hourly_rate = self._get_default_hourly_rate()

                # Subscriptions are prepaid: no per-session charge here
                if support_plan in ('monthly', 'yearly'):
                    return Decimal('0.00')

                # Hourly, custom or unknown -> charge per hour
                hours = Decimal(duration_minutes) / Decimal('60')
                amount = hours * effective_hourly_rate
                return amount.quantize(Decimal('0.01'))
                    
        except Exception as e:
            logger.error(f"Failed to calculate billing: {e}")
            return Decimal('0.00')
    
    def _create_payment_from_session(
        self,
        session_id: int,
        client_id: int,
        amount: Decimal,
        description: Optional[str] = None,
        remarks: Optional[str] = None
    ) -> Optional[int]:
        """
        Create a payment record from a completed session.
        
        Args:
            session_id: Session ID
            client_id: Client ID (family_id in payments table)
            amount: Payment amount
            
        Returns:
            Payment ID if created successfully, None otherwise
        """
        try:
            query = """
                INSERT INTO payments (
                    family_id, payment_date, description, remarks,
                    total_amount, paid_amount, remaining_amount, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'UNPAID')
            """
            
            description = description or f"Χρέωση συνεδρίας #{session_id}"
            
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(query, (
                    client_id,
                    datetime.now().date(),
                    description,
                    remarks,
                    amount,          # total_amount
                    Decimal('0.00'), # paid_amount
                    amount           # remaining_amount (this is the debt)
                ))
                payment_id = cursor.lastrowid
                
                # Link payment to session
                cursor.execute(
                    "UPDATE support_sessions SET payment_id = %s WHERE id = %s",
                    (payment_id, session_id)
                )
                
                connection.commit()
                
            logger.info(f"Created payment {payment_id} for session {session_id}")
            log_audit(self.db, 'payments', payment_id, 'INSERT', None,
                      {'family_id': client_id, 'amount': str(amount),
                       'description': description})
            return payment_id
            
        except Exception as e:
            logger.error(f"Failed to create payment from session: {e}")
            connection = self.db.get_connection()
            connection.rollback()
            return None
    
    def _deduct_prepaid_hours(self, client_id: int, duration_minutes: int) -> bool:
        """
        Deduct prepaid hours from client's package hours based on session duration.
        
        Args:
            client_id: Client ID
            duration_minutes: Session duration in minutes
            
        Returns:
            True if hours were deducted, False otherwise
        """
        try:
            # Convert minutes to hours
            session_hours = Decimal(duration_minutes) / Decimal('60')
            
            # Deduct across active, non-expired packages oldest-first, capping
            # each package so remaining_hours never goes negative.
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, remaining_hours, used_hours
                    FROM client_package_hours
                    WHERE client_id = %s AND is_active = 1
                    AND (expiry_date IS NULL OR expiry_date >= CURDATE())
                    AND remaining_hours > 0
                    ORDER BY expiry_date ASC, purchase_date ASC
                    """, (client_id,))
                pkgs = cursor.fetchall()
                to_deduct = session_hours
                any_deducted = False
                for pk in pkgs:
                    if to_deduct <= Decimal('0'):
                        break
                    avail = Decimal(str(pk['remaining_hours']))
                    used = Decimal(str(pk['used_hours']))
                    take = avail if avail < to_deduct else to_deduct
                    cursor.execute(
                        "UPDATE client_package_hours SET used_hours = %s WHERE id = %s",
                        (used + take, pk['id']))
                    to_deduct -= take
                    any_deducted = True
                connection.commit()
                if any_deducted:
                    logger.info(
                        f"Deducted {(session_hours - to_deduct):.2f}h from client "
                        f"{client_id} package hours")
                    return True
                logger.debug(f"No active prepaid hours found for client {client_id}")
                return False
                    
        except Exception as e:
            logger.error(f"Failed to deduct prepaid hours: {e}")
            connection = self.db.get_connection()
            connection.rollback()
            return False
