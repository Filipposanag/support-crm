# -*- coding: utf-8 -*-
"""
Maintenance Service
Provides database maintenance and data correction utilities.
"""

import logging
from typing import Tuple
from db.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class MaintenanceService:
    """
    Service for database maintenance operations.
    
    Provides utilities for:
    - Recalculating payment statuses
    - Data validation and correction
    - Database cleanup
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize MaintenanceService.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection
        logger.info("MaintenanceService initialized")
    
    def recalculate_payment_statuses(self) -> Tuple[int, int]:
        """
        Recalculate status for all payments based on amounts.
        
        Logic:
        - remaining_amount == 0 → status = "paid"
        - paid_amount > 0 AND remaining_amount > 0 → status = "partial"
        - otherwise → status = "unpaid"
        
        Returns:
            Tuple of (updated_count, total_count)
        """
        logger.info("Starting payment status recalculation")
        
        try:
            # Fetch all payments
            query = """
                SELECT id, total_amount, paid_amount, remaining_amount, status
                FROM payments
                ORDER BY id
            """
            
            payments = self.db.execute_query(query)
            total_count = len(payments)
            updated_count = 0
            
            logger.info(f"Found {total_count} payments to check")
            
            # Process each payment
            for payment in payments:
                payment_id = payment['id']
                total_amount = float(payment.get('total_amount', 0) or 0)
                paid_amount = float(payment.get('paid_amount', 0) or 0)
                remaining_amount = float(payment.get('remaining_amount', 0) or 0)
                current_status = payment.get('status', '')
                
                # Normalize current status
                normalized_status = (current_status or "").strip().lower()
                
                # Calculate correct status
                if remaining_amount == 0 and paid_amount > 0:
                    new_status = "paid"
                elif paid_amount > 0 and remaining_amount > 0:
                    new_status = "partial"
                else:
                    new_status = "unpaid"
                
                # Update if different
                if new_status != normalized_status:
                    update_query = "UPDATE payments SET status = %s WHERE id = %s"
                    self.db.execute_update(update_query, (new_status, payment_id))
                    updated_count += 1
                    
                    logger.debug(
                        f"Payment {payment_id}: '{normalized_status}' → '{new_status}' "
                        f"(total={total_amount}, paid={paid_amount}, remaining={remaining_amount})"
                    )
            
            logger.info(
                f"Payment status recalculation completed: "
                f"{updated_count} updated out of {total_count} total"
            )
            
            return (updated_count, total_count)
            
        except Exception as e:
            logger.error(f"Error during payment status recalculation: {e}", exc_info=True)
            raise
    
    def validate_payment_amounts(self) -> Tuple[int, int]:
        """
        Validate that payment amounts are consistent.
        
        Checks that: total_amount = paid_amount + remaining_amount
        
        Returns:
            Tuple of (inconsistent_count, total_count)
        """
        logger.info("Starting payment amount validation")
        
        try:
            query = """
                SELECT id, total_amount, paid_amount, remaining_amount
                FROM payments
                ORDER BY id
            """
            
            payments = self.db.execute_query(query)
            total_count = len(payments)
            inconsistent_count = 0
            
            for payment in payments:
                payment_id = payment['id']
                total_amount = float(payment.get('total_amount', 0) or 0)
                paid_amount = float(payment.get('paid_amount', 0) or 0)
                remaining_amount = float(payment.get('remaining_amount', 0) or 0)
                
                # Check if amounts are consistent (with small tolerance for floating point)
                calculated_total = paid_amount + remaining_amount
                if abs(total_amount - calculated_total) > 0.01:
                    inconsistent_count += 1
                    logger.warning(
                        f"Payment {payment_id}: Inconsistent amounts - "
                        f"total={total_amount}, paid={paid_amount}, remaining={remaining_amount}, "
                        f"calculated_total={calculated_total}"
                    )
            
            logger.info(
                f"Payment amount validation completed: "
                f"{inconsistent_count} inconsistent out of {total_count} total"
            )
            
            return (inconsistent_count, total_count)
            
        except Exception as e:
            logger.error(f"Error during payment amount validation: {e}", exc_info=True)
            raise
    
    def recalculate_family_members_count(self) -> Tuple[int, int]:
        """
        Recalculate members_count for all families based on actual active members.
        
        Returns:
            Tuple of (updated_count, total_count)
        """
        logger.info("Starting family members count recalculation")
        
        try:
            # Get all families with their actual member counts
            query = """
                SELECT 
                    f.id,
                    f.members_count as stored_count,
                    COUNT(m.id) as actual_count
                FROM families f
                LEFT JOIN members m ON f.id = m.family_id AND m.is_active = 1
                GROUP BY f.id
            """
            
            families = self.db.execute_query(query)
            total_count = len(families)
            updated_count = 0
            
            logger.info(f"Found {total_count} families to check")
            
            for family in families:
                family_id = family['id']
                stored_count = int(family.get('stored_count', 0) or 0)
                actual_count = int(family.get('actual_count', 0) or 0)
                
                if stored_count != actual_count:
                    update_query = "UPDATE families SET members_count = %s WHERE id = %s"
                    self.db.execute_update(update_query, (actual_count, family_id))
                    updated_count += 1
                    
                    logger.debug(
                        f"Family {family_id}: members_count {stored_count} → {actual_count}"
                    )
            
            logger.info(
                f"Family members count recalculation completed: "
                f"{updated_count} updated out of {total_count} total"
            )
            
            return (updated_count, total_count)
            
        except Exception as e:
            logger.error(f"Error during family members count recalculation: {e}", exc_info=True)
            raise
    
    def bulk_assign_receipt_numbers(self, prefix: str = 'ΑΠ', progress_callback=None) -> Tuple[int, int]:
        """
        Assign sequential receipt numbers to all payments ordered by date.
        
        Args:
            prefix: Prefix for receipt numbers
            progress_callback: Optional callback function(current, total, message)
            
        Returns:
            Tuple of (updated_count, total_count)
        """
        logger.info(f"Starting bulk receipt number assignment with prefix '{prefix}'")
        
        try:
            # Get all payments ordered by date, then by id
            query = """
                SELECT id, receipt_no, payment_date
                FROM payments
                ORDER BY payment_date ASC, id ASC
            """
            
            payments = self.db.execute_query(query)
            total_count = len(payments)
            updated_count = 0
            
            logger.info(f"Found {total_count} payments to number")
            
            if progress_callback:
                progress_callback(0, total_count, "Έναρξη αρίθμησης αποδείξεων...")
            
            # Assign sequential numbers
            for index, payment in enumerate(payments, start=1):
                payment_id = payment['id']
                new_receipt_no = f"{prefix}-{index:04d}"
                
                update_query = "UPDATE payments SET receipt_no = %s WHERE id = %s"
                self.db.execute_update(update_query, (new_receipt_no, payment_id))
                updated_count += 1
                
                if progress_callback and (updated_count % 10 == 0 or updated_count == total_count):
                    progress_callback(updated_count, total_count, f"Αρίθμηση απόδειξης {updated_count}/{total_count}")
                
                if updated_count % 100 == 0:
                    logger.debug(f"Processed {updated_count}/{total_count} payments")
            
            # Commit all changes
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(
                f"Bulk receipt number assignment completed: "
                f"{updated_count} payments numbered"
            )
            
            return (updated_count, total_count)
            
        except Exception as e:
            logger.error(f"Error during bulk receipt number assignment: {e}", exc_info=True)
            # Rollback on error
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise
    
    def bulk_assign_subscription_codes(self, prefix: str = 'ΣΥΝ', progress_callback=None) -> Tuple[int, int]:
        """
        Assign sequential subscription codes to all payments ordered by date.
        
        Args:
            prefix: Prefix for subscription codes
            progress_callback: Optional callback function(current, total, message)
            
        Returns:
            Tuple of (updated_count, total_count)
        """
        logger.info(f"Starting bulk subscription code assignment with prefix '{prefix}'")
        
        try:
            # Get all payments ordered by date, then by id
            query = """
                SELECT id, subscription_code, payment_date
                FROM payments
                ORDER BY payment_date ASC, id ASC
            """
            
            payments = self.db.execute_query(query)
            total_count = len(payments)
            updated_count = 0
            
            logger.info(f"Found {total_count} payments to code")
            
            if progress_callback:
                progress_callback(0, total_count, "Έναρξη αρίθμησης συνδρομών...")
            
            # Assign sequential codes
            for index, payment in enumerate(payments, start=1):
                payment_id = payment['id']
                new_subscription_code = f"{prefix}-{index:04d}"
                
                update_query = "UPDATE payments SET subscription_code = %s WHERE id = %s"
                self.db.execute_update(update_query, (new_subscription_code, payment_id))
                updated_count += 1
                
                if progress_callback and (updated_count % 10 == 0 or updated_count == total_count):
                    progress_callback(updated_count, total_count, f"Αρίθμηση συνδρομής {updated_count}/{total_count}")
                
                if updated_count % 100 == 0:
                    logger.debug(f"Processed {updated_count}/{total_count} payments")
            
            # Commit all changes
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(
                f"Bulk subscription code assignment completed: "
                f"{updated_count} payments coded"
            )
            
            return (updated_count, total_count)
            
        except Exception as e:
            logger.error(f"Error during bulk subscription code assignment: {e}", exc_info=True)
            # Rollback on error
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise
    
    def bulk_assign_family_codes(self, start_number: int = 1, progress_callback=None) -> Tuple[int, int]:
        """
        Assign sequential legacy_code to all families ordered by creation date.
        Uses the legacy_code field (integer).
        
        Args:
            start_number: Starting number for legacy_code (default: 1)
            progress_callback: Optional callback function(current, total, message)
            
        Returns:
            Tuple of (updated_count, total_count)
        """
        logger.info(f"Starting bulk family numbering with start_number={start_number}")
        
        try:
            # Get all families ordered by created_at, then by id
            query = """
                SELECT id, legacy_code, created_at
                FROM families
                ORDER BY created_at ASC, id ASC
            """
            
            families = self.db.execute_query(query)
            total_count = len(families)
            updated_count = 0
            
            logger.info(f"Found {total_count} families to number")
            
            if progress_callback:
                progress_callback(0, total_count, "Έναρξη αρίθμησης οικογενειών...")
            
            # Assign sequential numbers
            for index, family in enumerate(families, start=start_number):
                family_id = family['id']
                new_legacy_code = index
                
                update_query = "UPDATE families SET legacy_code = %s WHERE id = %s"
                self.db.execute_update(update_query, (new_legacy_code, family_id))
                updated_count += 1
                
                if progress_callback and (updated_count % 10 == 0 or updated_count == total_count):
                    progress_callback(updated_count, total_count, f"Αρίθμηση πελάτη {updated_count}/{total_count}")
                
                if updated_count % 100 == 0:
                    logger.debug(f"Processed {updated_count}/{total_count} families")
            
            # Commit all changes
            connection = self.db.get_connection()
            connection.commit()
            
            logger.info(
                f"Bulk family numbering completed: "
                f"{updated_count} families numbered"
            )
            
            return (updated_count, total_count)
            
        except Exception as e:
            logger.error(f"Error during bulk family code assignment: {e}", exc_info=True)
            # Rollback on error
            try:
                connection = self.db.get_connection()
                connection.rollback()
            except:
                pass
            raise

    def repair_subscriptions_table(self) -> dict:
        """
        Repair subscriptions table by:
        1. Adding subscription_code column if missing
        2. Creating index for subscription_code
        3. Copying subscription_code from payments
        4. Checking for duplicates and constraints
        
        Returns:
            Dictionary with repair results and status messages
        """
        logger.info("Starting subscriptions table repair")
        
        results = {
            'success': True,
            'messages': [],
            'errors': [],
            'stats': {}
        }
        
        try:
            from pymysql.cursors import DictCursor
            connection = self.db.get_connection()
            cursor = connection.cursor(DictCursor)
            
            # Step 1: Check and add subscription_code column
            try:
                check_column_query = """
                    SELECT COUNT(*) as col_count
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'subscriptions'
                      AND COLUMN_NAME = 'subscription_code'
                """
                cursor.execute(check_column_query)
                result = cursor.fetchone()
                column_exists = result['col_count'] > 0 if result else False
                
                if not column_exists:
                    alter_query = """
                        ALTER TABLE subscriptions 
                        ADD COLUMN subscription_code VARCHAR(50) 
                        COMMENT 'Subscription code (copied from payment)'
                    """
                    cursor.execute(alter_query)
                    connection.commit()
                    results['messages'].append("✓ Προστέθηκε η στήλη subscription_code")
                    logger.info("Added subscription_code column")
                else:
                    results['messages'].append("✓ Η στήλη subscription_code ήδη υπάρχει")
                    logger.info("subscription_code column already exists")
            except Exception as e:
                error_msg = f"Σφάλμα προσθήκης στήλης: {type(e).__name__}: {str(e) if str(e) else repr(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg, exc_info=True)
            
            # Step 2: Check and create index
            try:
                check_index_query = """
                    SELECT COUNT(*) as idx_count
                    FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'subscriptions'
                      AND INDEX_NAME = 'idx_subscriptions_code'
                """
                cursor.execute(check_index_query)
                result = cursor.fetchone()
                index_exists = result['idx_count'] > 0 if result else False
                
                if not index_exists:
                    create_index_query = """
                        CREATE INDEX idx_subscriptions_code 
                        ON subscriptions(subscription_code)
                    """
                    cursor.execute(create_index_query)
                    connection.commit()
                    results['messages'].append("✓ Δημιουργήθηκε το index idx_subscriptions_code")
                    logger.info("Created idx_subscriptions_code index")
                else:
                    results['messages'].append("✓ Το index idx_subscriptions_code ήδη υπάρχει")
                    logger.info("idx_subscriptions_code index already exists")
            except Exception as e:
                error_msg = f"Σφάλμα δημιουργίας index: {type(e).__name__}: {str(e) if str(e) else repr(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg, exc_info=True)
            
            # Step 3: Copy subscription_code from payments
            try:
                copy_query = """
                    UPDATE subscriptions s
                    INNER JOIN payments p ON s.payment_id = p.id
                    SET s.subscription_code = p.subscription_code
                    WHERE (s.subscription_code IS NULL OR s.subscription_code = '')
                      AND p.subscription_code IS NOT NULL 
                      AND p.subscription_code != ''
                """
                cursor.execute(copy_query)
                copied_count = cursor.rowcount
                connection.commit()
                results['messages'].append(f"✓ Αντιγράφηκαν {copied_count} subscription codes")
                results['stats']['copied_codes'] = copied_count
                logger.info(f"Copied {copied_count} subscription codes from payments")
            except Exception as e:
                error_msg = f"Σφάλμα αντιγραφής κωδικών: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
            
            # Step 4: Check for UNIQUE constraint
            try:
                check_constraint_query = """
                    SELECT COUNT(*) as constraint_count
                    FROM information_schema.TABLE_CONSTRAINTS
                    WHERE CONSTRAINT_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'subscriptions'
                      AND CONSTRAINT_NAME = 'uq_subscriptions_family_year'
                      AND CONSTRAINT_TYPE = 'UNIQUE'
                """
                cursor.execute(check_constraint_query)
                result = cursor.fetchone()
                constraint_exists = result['constraint_count'] > 0 if result else False
                
                if constraint_exists:
                    results['messages'].append("✓ Το UNIQUE constraint υπάρχει")
                else:
                    results['messages'].append("⚠ Το UNIQUE constraint ΔΕΝ υπάρχει - τρέξτε το Migration 018")
                    logger.warning("UNIQUE constraint missing")
            except Exception as e:
                error_msg = f"Σφάλμα ελέγχου constraint: {type(e).__name__}: {str(e) if str(e) else repr(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg, exc_info=True)
            
            # Step 5: Check triggers
            try:
                check_triggers_query = """
                    SELECT COUNT(*) as trigger_count
                    FROM information_schema.TRIGGERS
                    WHERE EVENT_OBJECT_SCHEMA = DATABASE()
                      AND EVENT_OBJECT_TABLE = 'families'
                      AND TRIGGER_NAME IN (
                          'trg_families_after_insert',
                          'trg_families_after_update',
                          'trg_families_after_delete'
                      )
                """
                cursor.execute(check_triggers_query)
                result = cursor.fetchone()
                trigger_count = result['trigger_count'] if result else 0
                
                if trigger_count == 3:
                    results['messages'].append("✓ Όλα τα triggers υπάρχουν (3/3)")
                else:
                    results['messages'].append(f"⚠ Λείπουν triggers: {3 - trigger_count}/3")
                    logger.warning(f"Missing {3 - trigger_count} triggers")
                
                results['stats']['triggers'] = trigger_count
            except Exception as e:
                error_msg = f"Σφάλμα ελέγχου triggers: {type(e).__name__}: {str(e) if str(e) else repr(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg, exc_info=True)
            
            # Step 6: Check for duplicates
            try:
                check_duplicates_query = """
                    SELECT COUNT(*) as duplicate_count
                    FROM (
                        SELECT family_id, year, COUNT(*) as count
                        FROM subscriptions
                        GROUP BY family_id, year
                        HAVING count > 1
                    ) as duplicates
                """
                cursor.execute(check_duplicates_query)
                result = cursor.fetchone()
                duplicate_count = result['duplicate_count'] if result else 0
                
                if duplicate_count == 0:
                    results['messages'].append("✓ Δεν υπάρχουν διπλές συνδρομές")
                else:
                    results['messages'].append(f"⚠ Βρέθηκαν {duplicate_count} διπλές συνδρομές")
                    logger.warning(f"Found {duplicate_count} duplicate subscriptions")
                
                results['stats']['duplicates'] = duplicate_count
            except Exception as e:
                error_msg = f"Σφάλμα ελέγχου διπλότυπων: {type(e).__name__}: {str(e) if str(e) else repr(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg, exc_info=True)
            
            # Step 7: Get final statistics
            try:
                stats_query = """
                    SELECT 
                        COUNT(*) as total_subscriptions,
                        SUM(CASE WHEN subscription_code IS NOT NULL AND subscription_code != '' THEN 1 ELSE 0 END) as with_code,
                        SUM(CASE WHEN subscription_code IS NULL OR subscription_code = '' THEN 1 ELSE 0 END) as without_code
                    FROM subscriptions
                """
                cursor.execute(stats_query)
                stats = cursor.fetchone()
                
                results['stats']['total'] = stats['total_subscriptions'] if stats else 0
                results['stats']['with_code'] = stats['with_code'] if stats else 0
                results['stats']['without_code'] = stats['without_code'] if stats else 0
                
                results['messages'].append(f"\n📊 Στατιστικά:")
                results['messages'].append(f"   • Σύνολο συνδρομών: {results['stats']['total']}")
                results['messages'].append(f"   • Με κωδικό: {results['stats']['with_code']}")
                results['messages'].append(f"   • Χωρίς κωδικό: {results['stats']['without_code']}")
                
                logger.info(f"Final stats: total={results['stats']['total']}, with_code={results['stats']['with_code']}, without_code={results['stats']['without_code']}")
            except Exception as e:
                error_msg = f"Σφάλμα συλλογής στατιστικών: {type(e).__name__}: {str(e) if str(e) else repr(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg, exc_info=True)
            
            cursor.close()
            
            # Step 8: Repair audit triggers
            results['messages'].append("\n🔧 Έλεγχος Audit Triggers:")
            try:
                audit_results = self.repair_audit_triggers()
                
                if audit_results['success']:
                    results['messages'].append("✓ Audit triggers διορθώθηκαν")
                    results['messages'].extend([f"   {msg}" for msg in audit_results['messages']])
                else:
                    results['messages'].append("⚠ Audit triggers: Υπήρξαν προβλήματα")
                    results['errors'].extend(audit_results['errors'])
                
                # Merge stats
                if 'triggers' in audit_results.get('stats', {}):
                    results['stats']['audit_triggers'] = audit_results['stats']['triggers']
                    
            except Exception as e:
                error_msg = f"Σφάλμα επιδιόρθωσης audit triggers: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
            
            if results['errors']:
                results['success'] = False
            
            logger.info(f"Database repair completed with {len(results['errors'])} errors")
            
            return results
            
        except Exception as e:
            logger.error(f"Critical error during database repair: {e}", exc_info=True)
            results['success'] = False
            results['errors'].append(f"Κρίσιμο σφάλμα: {str(e)}")
            return results

    def repair_audit_triggers(self) -> dict:
        """
        Repair audit log triggers by recreating them without family_number reference.
        
        Returns:
            Dictionary with repair results and status messages
        """
        logger.info("Starting audit triggers repair")
        
        results = {
            'success': True,
            'messages': [],
            'errors': [],
            'stats': {}
        }
        
        try:
            from pymysql.cursors import DictCursor
            connection = self.db.get_connection()
            cursor = connection.cursor(DictCursor)
            
            # Step 1: Check if audit_log table exists
            try:
                check_table_query = """
                    SELECT COUNT(*) as count
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'audit_log'
                """
                cursor.execute(check_table_query)
                table_exists = cursor.fetchone()['count'] > 0
                
                if not table_exists:
                    results['errors'].append("⚠ Ο πίνακας audit_log δεν υπάρχει")
                    results['success'] = False
                    return results
                
                results['messages'].append("✓ Ο πίνακας audit_log υπάρχει")
            except Exception as e:
                error_msg = f"Σφάλμα ελέγχου πίνακα: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
            
            # Step 2: Drop old triggers
            try:
                cursor.execute("DROP TRIGGER IF EXISTS trg_families_after_insert")
                cursor.execute("DROP TRIGGER IF EXISTS trg_families_after_update")
                cursor.execute("DROP TRIGGER IF EXISTS trg_families_after_delete")
                connection.commit()
                results['messages'].append("✓ Διαγράφηκαν τα παλιά triggers")
                logger.info("Dropped old family triggers")
            except Exception as e:
                error_msg = f"Σφάλμα διαγραφής triggers: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
            
            # Step 3: Create new triggers
            try:
                # Trigger: After INSERT
                cursor.execute("""
                    CREATE TRIGGER trg_families_after_insert
                    AFTER INSERT ON families
                    FOR EACH ROW
                    BEGIN
                        INSERT INTO audit_log (table_name, record_id, operation, new_values)
                        VALUES (
                            'families',
                            NEW.id,
                            'INSERT',
                            JSON_OBJECT(
                                'legacy_code', NEW.legacy_code,
                                'last_name', NEW.last_name,
                                'first_name', NEW.first_name,
                                'phone', NEW.phone,
                                'email', NEW.email,
                                'is_active', NEW.is_active
                            )
                        );
                    END
                """)
                
                # Trigger: After UPDATE
                cursor.execute("""
                    CREATE TRIGGER trg_families_after_update
                    AFTER UPDATE ON families
                    FOR EACH ROW
                    BEGIN
                        INSERT INTO audit_log (table_name, record_id, operation, old_values, new_values)
                        VALUES (
                            'families',
                            NEW.id,
                            'UPDATE',
                            JSON_OBJECT(
                                'legacy_code', OLD.legacy_code,
                                'last_name', OLD.last_name,
                                'first_name', OLD.first_name,
                                'phone', OLD.phone,
                                'email', OLD.email,
                                'is_active', OLD.is_active
                            ),
                            JSON_OBJECT(
                                'legacy_code', NEW.legacy_code,
                                'last_name', NEW.last_name,
                                'first_name', NEW.first_name,
                                'phone', NEW.phone,
                                'email', NEW.email,
                                'is_active', NEW.is_active
                            )
                        );
                    END
                """)
                
                # Trigger: After DELETE
                cursor.execute("""
                    CREATE TRIGGER trg_families_after_delete
                    AFTER DELETE ON families
                    FOR EACH ROW
                    BEGIN
                        INSERT INTO audit_log (table_name, record_id, operation, old_values)
                        VALUES (
                            'families',
                            OLD.id,
                            'DELETE',
                            JSON_OBJECT(
                                'legacy_code', OLD.legacy_code,
                                'last_name', OLD.last_name,
                                'first_name', OLD.first_name,
                                'phone', OLD.phone,
                                'email', OLD.email,
                                'is_active', OLD.is_active
                            )
                        );
                    END
                """)
                
                connection.commit()
                results['messages'].append("✓ Δημιουργήθηκαν νέα triggers (3/3)")
                logger.info("Created new family triggers")
            except Exception as e:
                error_msg = f"Σφάλμα δημιουργίας triggers: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
            
            # Step 4: Verify triggers
            try:
                check_triggers_query = """
                    SELECT COUNT(*) as trigger_count
                    FROM information_schema.TRIGGERS
                    WHERE EVENT_OBJECT_SCHEMA = DATABASE()
                      AND EVENT_OBJECT_TABLE = 'families'
                """
                cursor.execute(check_triggers_query)
                trigger_count = cursor.fetchone()['trigger_count']
                
                if trigger_count == 3:
                    results['messages'].append("✓ Όλα τα triggers επαληθεύτηκαν (3/3)")
                else:
                    results['messages'].append(f"⚠ Βρέθηκαν {trigger_count}/3 triggers")
                    logger.warning(f"Only {trigger_count}/3 triggers found")
                
                results['stats']['triggers'] = trigger_count
            except Exception as e:
                error_msg = f"Σφάλμα επαλήθευσης triggers: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
            
            # Step 5: Test triggers
            try:
                # Insert test record
                cursor.execute("""
                    INSERT INTO families (legacy_code, last_name, first_name, is_active)
                    VALUES (99999, 'TEST', 'AUDIT', 1)
                """)
                test_id = cursor.lastrowid
                connection.commit()
                
                # Check if audit log was created
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM audit_log 
                    WHERE table_name = 'families' AND record_id = %s
                """, (test_id,))
                audit_count = cursor.fetchone()['count']
                
                # Delete test record
                cursor.execute("DELETE FROM families WHERE id = %s", (test_id,))
                connection.commit()
                
                if audit_count > 0:
                    results['messages'].append("✓ Δοκιμή triggers επιτυχής")
                    logger.info("Trigger test successful")
                else:
                    results['messages'].append("⚠ Δοκιμή triggers απέτυχε")
                    logger.warning("Trigger test failed")
                
                results['stats']['test_passed'] = audit_count > 0
            except Exception as e:
                error_msg = f"Σφάλμα δοκιμής triggers: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
            
            cursor.close()
            
            if results['errors']:
                results['success'] = False
            
            logger.info(f"Audit triggers repair completed with {len(results['errors'])} errors")
            
            return results
            
        except Exception as e:
            logger.error(f"Critical error during audit triggers repair: {e}", exc_info=True)
            results['success'] = False
            results['errors'].append(f"Κρίσιμο σφάλμα: {str(e)}")
            return results

    def repair_app_settings_table(self) -> dict:
        """
        Repair app_settings table by adding missing columns.
        
        Checks and adds:
        - auto_check_updates column
        - Any other missing columns from schema
        
        Returns:
            Dictionary with repair results and status messages
        """
        logger.info("Starting app_settings table repair")
        
        results = {
            'success': True,
            'messages': [],
            'errors': [],
            'stats': {}
        }
        
        try:
            # Check and add auto_check_updates column
            try:
                check_column_query = """
                    SELECT COUNT(*) as cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'app_settings'
                      AND COLUMN_NAME = 'auto_check_updates'
                """
                result = self.db.execute_query(check_column_query)
                column_exists = result[0]['cnt'] > 0 if result else False
                
                if not column_exists:
                    alter_query = """
                        ALTER TABLE app_settings 
                        ADD COLUMN auto_check_updates TINYINT(1) DEFAULT 1 
                        COMMENT 'Enable automatic update checking on startup'
                    """
                    self.db.execute_update(alter_query)
                    self.db.commit()
                    results['messages'].append("✓ Προστέθηκε η στήλη auto_check_updates")
                    logger.info("Added auto_check_updates column")
                    
                    # Set default value for existing row
                    try:
                        update_query = "UPDATE app_settings SET auto_check_updates = 1 WHERE id = 1"
                        self.db.execute_update(update_query)
                        self.db.commit()
                        results['messages'].append("✓ Ορίστηκε default τιμή για auto_check_updates")
                    except Exception as e:
                        logger.warning(f"Could not set default value: {e}")
                else:
                    results['messages'].append("✓ Η στήλη auto_check_updates ήδη υπάρχει")
                    logger.info("auto_check_updates column already exists")
            except Exception as e:
                # Extract error message properly
                error_detail = str(e) if str(e) else repr(e)
                error_msg = f"Σφάλμα προσθήκης στήλης auto_check_updates: {error_detail}"
                results['errors'].append(error_msg)
                results['success'] = False
                logger.error(error_msg, exc_info=True)
            
            if results['errors']:
                results['success'] = False
            
            logger.info(f"app_settings repair completed with {len(results['errors'])} errors")
            
            return results
            
        except Exception as e:
            logger.error(f"Critical error during app_settings repair: {e}", exc_info=True)
            results['success'] = False
            results['errors'].append(f"Κρίσιμο σφάλμα: {str(e)}")
            return results

    def sync_subscriptions_from_payments(self, progress_callback=None) -> dict:
        """
        Συγχρονίζει τον πίνακα subscriptions με βάση τις πληρωμές.
        Για κάθε πληρωμή που έχει subscription_start_date και subscription_end_date:
        - Αν υπάρχει ήδη subscription για τον πελάτη και το έτος, το ενημερώνει
        - Αν δεν υπάρχει, το δημιουργεί
        
        Args:
            progress_callback: Optional callback function(current, total, message)
            
        Returns:
            Dictionary με αποτελέσματα (created, updated, skipped, errors)
        """
        logger.info("Starting subscriptions sync from payments")
        
        results = {
            'success': True,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
            'messages': []
        }
        
        try:
            from pymysql.cursors import DictCursor
            connection = self.db.get_connection()
            cursor = connection.cursor(DictCursor)
            
            # Βρες όλες τις πληρωμές που έχουν subscription dates
            query = """
                SELECT 
                    p.id as payment_id,
                    p.family_id,
                    p.year,
                    p.subscription_code,
                    p.subscription_start_date,
                    p.subscription_end_date,
                    p.payment_date,
                    p.total_amount,
                    p.paid_amount,
                    p.remaining_amount,
                    p.status,
                    f.last_name,
                    f.first_name
                FROM payments p
                INNER JOIN families f ON p.family_id = f.id
                WHERE p.subscription_start_date IS NOT NULL 
                  AND p.subscription_end_date IS NOT NULL
                ORDER BY p.family_id, p.year, p.payment_date
            """
            
            cursor.execute(query)
            payments = cursor.fetchall()
            total_count = len(payments)
            
            logger.info(f"Found {total_count} payments with subscription dates")
            results['messages'].append(f"Βρέθηκαν {total_count} πληρωμές με ημερομηνίες συνδρομής")
            
            if progress_callback:
                progress_callback(0, total_count, "Έναρξη συγχρονισμού συνδρομών...")
            
            processed = 0
            
            for payment in payments:
                try:
                    family_id = payment['family_id']
                    year = payment['year']
                    payment_id = payment['payment_id']
                    
                    # Έλεγξε αν υπάρχει ήδη subscription για αυτόν τον πελάτη και έτος
                    check_query = """
                        SELECT id, payment_id 
                        FROM subscriptions 
                        WHERE family_id = %s AND year = %s
                    """
                    cursor.execute(check_query, (family_id, year))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Ενημέρωση υπάρχουσας συνδρομής
                        subscription_id = existing['id']
                        
                        # Υπολόγισε την κατάσταση
                        subscription_status = self._calculate_subscription_status(
                            payment['subscription_start_date'],
                            payment['subscription_end_date'],
                            payment['remaining_amount']
                        )
                        
                        update_query = """
                            UPDATE subscriptions SET
                                payment_id = %s,
                                subscription_code = %s,
                                start_date = %s,
                                end_date = %s,
                                status = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """
                        
                        cursor.execute(update_query, (
                            payment_id,
                            payment['subscription_code'],
                            payment['subscription_start_date'],
                            payment['subscription_end_date'],
                            subscription_status,
                            subscription_id
                        ))
                        
                        results['updated'] += 1
                        logger.debug(f"Updated subscription id={subscription_id} for family={family_id}, year={year}")
                    
                    else:
                        # Δημιουργία νέας συνδρομής
                        subscription_status = self._calculate_subscription_status(
                            payment['subscription_start_date'],
                            payment['subscription_end_date'],
                            payment['remaining_amount']
                        )
                        
                        insert_query = """
                            INSERT INTO subscriptions (
                                family_id,
                                year,
                                payment_id,
                                subscription_code,
                                start_date,
                                end_date,
                                status,
                                created_at,
                                updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """
                        
                        cursor.execute(insert_query, (
                            family_id,
                            year,
                            payment_id,
                            payment['subscription_code'],
                            payment['subscription_start_date'],
                            payment['subscription_end_date'],
                            subscription_status
                        ))
                        
                        results['created'] += 1
                        logger.debug(f"Created subscription for family={family_id}, year={year}")
                    
                    processed += 1
                    
                    # Progress callback
                    if progress_callback and (processed % 10 == 0 or processed == total_count):
                        family_name = f"{payment['last_name']} {payment['first_name']}"
                        progress_callback(
                            processed, 
                            total_count, 
                            f"Επεξεργασία: {family_name} ({year})"
                        )
                    
                    # Commit every 50 records
                    if processed % 50 == 0:
                        connection.commit()
                
                except Exception as e:
                    error_msg = f"Σφάλμα στην πληρωμή id={payment.get('payment_id')}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg, exc_info=True)
                    results['skipped'] += 1
            
            # Final commit
            connection.commit()
            cursor.close()
            
            # Σύνοψη
            results['messages'].append(f"\n✓ Δημιουργήθηκαν: {results['created']} συνδρομές")
            results['messages'].append(f"✓ Ενημερώθηκαν: {results['updated']} συνδρομές")
            
            if results['skipped'] > 0:
                results['messages'].append(f"⚠ Παραλείφθηκαν: {results['skipped']} (λόγω σφαλμάτων)")
            
            if results['errors']:
                results['success'] = False
                results['messages'].append(f"\n❌ Σφάλματα: {len(results['errors'])}")
            
            logger.info(
                f"Subscriptions sync completed: "
                f"created={results['created']}, updated={results['updated']}, "
                f"skipped={results['skipped']}, errors={len(results['errors'])}"
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Critical error during subscriptions sync: {e}", exc_info=True)
            results['success'] = False
            results['errors'].append(f"Κρίσιμο σφάλμα: {str(e)}")
            return results
    
    def _calculate_subscription_status(self, start_date, end_date, remaining_amount) -> str:
        """
        Υπολογίζει την κατάσταση μιας συνδρομής.
        
        Args:
            start_date: Ημερομηνία έναρξης
            end_date: Ημερομηνία λήξης
            remaining_amount: Υπόλοιπο ποσό
            
        Returns:
            Κατάσταση: 'active', 'expired', 'pending', 'cancelled'
        """
        from datetime import date
        
        if not start_date or not end_date:
            return 'pending'
        
        today = date.today()
        
        # Μετατροπή σε date objects αν χρειάζεται
        if isinstance(start_date, str):
            from datetime import datetime
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            from datetime import datetime
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Έλεγχος αν έχει λήξει
        if end_date < today:
            return 'expired'
        
        # Έλεγχος αν έχει ξεκινήσει
        if start_date > today:
            return 'pending'
        
        # Ενεργή συνδρομή
        return 'active'

    def find_duplicate_records(self) -> dict:
        """
        Find duplicate records across all main tables.
        
        Checks for duplicates in:
        - families: Same last_name + first_name + phone/mobile
        - members: Same family_id + first_name + last_name
        - payments: Same family_id + payment_date + total_amount
        - subscriptions: Same family_id + year (already has UNIQUE constraint)
        
        Returns:
            Dictionary with duplicate records per table
        """
        logger.info("Starting duplicate records search")
        
        results = {
            'families': [],
            'members': [],
            'payments': [],
            'subscriptions': [],
            'total_duplicates': 0
        }
        
        try:
            from pymysql.cursors import DictCursor
            connection = self.db.get_connection()
            cursor = connection.cursor(DictCursor)
            
            # 1. Find duplicate families (same name + phone/mobile)
            families_query = """
                SELECT 
                    f1.id, f1.legacy_code, f1.last_name, f1.first_name, 
                    f1.phone, f1.mobile, f1.email, f1.created_at,
                    GROUP_CONCAT(f2.id ORDER BY f2.id) as duplicate_ids
                FROM families f1
                INNER JOIN families f2 ON 
                    f1.last_name = f2.last_name 
                    AND f1.first_name = f2.first_name
                    AND f1.id < f2.id
                    AND (
                        (f1.phone != '' AND f1.phone = f2.phone)
                        OR (f1.mobile != '' AND f1.mobile = f2.mobile)
                        OR (f1.email != '' AND f1.email = f2.email)
                    )
                WHERE f1.is_active = 1
                GROUP BY f1.id
                ORDER BY f1.last_name, f1.first_name
            """
            cursor.execute(families_query)
            results['families'] = cursor.fetchall()
            
            # 2. Find duplicate members (same family + name)
            members_query = """
                SELECT 
                    m1.id, m1.family_id, m1.first_name, m1.last_name,
                    m1.birth_date, m1.created_at,
                    f.last_name as family_name,
                    GROUP_CONCAT(m2.id ORDER BY m2.id) as duplicate_ids
                FROM members m1
                INNER JOIN members m2 ON 
                    m1.family_id = m2.family_id
                    AND m1.first_name = m2.first_name
                    AND COALESCE(m1.last_name, '') = COALESCE(m2.last_name, '')
                    AND m1.id < m2.id
                LEFT JOIN families f ON m1.family_id = f.id
                WHERE m1.is_active = 1
                GROUP BY m1.id
                ORDER BY f.last_name, m1.first_name
            """
            cursor.execute(members_query)
            results['members'] = cursor.fetchall()
            
            # 3. Find duplicate payments (same family + date + amount)
            payments_query = """
                SELECT 
                    p1.id, p1.family_id, p1.payment_date, p1.total_amount,
                    p1.receipt_no, p1.description, p1.created_at,
                    f.last_name as family_name, f.first_name as family_first_name,
                    GROUP_CONCAT(p2.id ORDER BY p2.id) as duplicate_ids
                FROM payments p1
                INNER JOIN payments p2 ON 
                    p1.family_id = p2.family_id
                    AND p1.payment_date = p2.payment_date
                    AND p1.total_amount = p2.total_amount
                    AND p1.id < p2.id
                LEFT JOIN families f ON p1.family_id = f.id
                GROUP BY p1.id
                ORDER BY p1.payment_date DESC, f.last_name
            """
            cursor.execute(payments_query)
            results['payments'] = cursor.fetchall()
            
            # 4. Find duplicate subscriptions (same family + year)
            subscriptions_query = """
                SELECT 
                    s1.id, s1.family_id, s1.year, s1.status,
                    s1.total_amount, s1.created_at,
                    f.last_name as family_name, f.first_name as family_first_name,
                    GROUP_CONCAT(s2.id ORDER BY s2.id) as duplicate_ids
                FROM subscriptions s1
                INNER JOIN subscriptions s2 ON 
                    s1.family_id = s2.family_id
                    AND s1.year = s2.year
                    AND s1.id < s2.id
                LEFT JOIN families f ON s1.family_id = f.id
                GROUP BY s1.id
                ORDER BY s1.year DESC, f.last_name
            """
            cursor.execute(subscriptions_query)
            results['subscriptions'] = cursor.fetchall()
            
            cursor.close()
            
            # Calculate totals
            results['total_duplicates'] = (
                len(results['families']) + 
                len(results['members']) + 
                len(results['payments']) + 
                len(results['subscriptions'])
            )
            
            logger.info(
                f"Duplicate search completed: "
                f"families={len(results['families'])}, "
                f"members={len(results['members'])}, "
                f"payments={len(results['payments'])}, "
                f"subscriptions={len(results['subscriptions'])}"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error during duplicate search: {e}", exc_info=True)
            raise
    
    def merge_duplicate_families(self, keep_id: int, delete_ids: list) -> dict:
        """
        Merge duplicate families by moving all related records to the kept family
        and deleting the duplicate families.
        
        Args:
            keep_id: ID of the family to keep
            delete_ids: List of family IDs to merge into keep_id and delete
            
        Returns:
            Dictionary with merge results
        """
        logger.info(f"Merging families: keep={keep_id}, delete={delete_ids}")
        
        results = {
            'success': True,
            'members_moved': 0,
            'payments_moved': 0,
            'subscriptions_moved': 0,
            'families_deleted': 0,
            'errors': []
        }
        
        try:
            from pymysql.cursors import DictCursor
            connection = self.db.get_connection()
            cursor = connection.cursor(DictCursor)
            
            for delete_id in delete_ids:
                try:
                    # Move members
                    cursor.execute(
                        "UPDATE members SET family_id = %s WHERE family_id = %s",
                        (keep_id, delete_id)
                    )
                    results['members_moved'] += cursor.rowcount
                    
                    # Move payments
                    cursor.execute(
                        "UPDATE payments SET family_id = %s WHERE family_id = %s",
                        (keep_id, delete_id)
                    )
                    results['payments_moved'] += cursor.rowcount
                    
                    # Handle subscriptions (may have UNIQUE constraint on family_id + year)
                    # First check for conflicts
                    cursor.execute("""
                        SELECT s1.id, s1.year 
                        FROM subscriptions s1
                        WHERE s1.family_id = %s
                        AND EXISTS (
                            SELECT 1 FROM subscriptions s2 
                            WHERE s2.family_id = %s AND s2.year = s1.year
                        )
                    """, (delete_id, keep_id))
                    conflicts = cursor.fetchall()
                    
                    if conflicts:
                        # Delete conflicting subscriptions from the duplicate
                        for conflict in conflicts:
                            cursor.execute(
                                "DELETE FROM subscriptions WHERE id = %s",
                                (conflict['id'],)
                            )
                            logger.info(f"Deleted conflicting subscription {conflict['id']} for year {conflict['year']}")
                    
                    # Move remaining subscriptions
                    cursor.execute(
                        "UPDATE subscriptions SET family_id = %s WHERE family_id = %s",
                        (keep_id, delete_id)
                    )
                    results['subscriptions_moved'] += cursor.rowcount
                    
                    # Delete the duplicate family
                    cursor.execute(
                        "DELETE FROM families WHERE id = %s",
                        (delete_id,)
                    )
                    results['families_deleted'] += cursor.rowcount
                    
                    logger.info(f"Merged family {delete_id} into {keep_id}")
                    
                except Exception as e:
                    error_msg = f"Error merging family {delete_id}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
            
            connection.commit()
            cursor.close()
            
            # Recalculate members count for the kept family
            self.recalculate_family_members_count()
            
            if results['errors']:
                results['success'] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Error during family merge: {e}", exc_info=True)
            try:
                connection.rollback()
            except:
                pass
            raise
    
    def delete_duplicate_records(self, table: str, keep_id: int, delete_ids: list) -> dict:
        """
        Delete duplicate records from a table, keeping one record.
        
        Args:
            table: Table name ('members', 'payments', 'subscriptions')
            keep_id: ID of the record to keep
            delete_ids: List of record IDs to delete
            
        Returns:
            Dictionary with deletion results
        """
        logger.info(f"Deleting duplicates from {table}: keep={keep_id}, delete={delete_ids}")
        
        results = {
            'success': True,
            'deleted_count': 0,
            'errors': []
        }
        
        # Validate table name
        valid_tables = ['members', 'payments', 'subscriptions']
        if table not in valid_tables:
            results['success'] = False
            results['errors'].append(f"Invalid table: {table}")
            return results
        
        try:
            connection = self.db.get_connection()
            cursor = connection.cursor()
            
            for delete_id in delete_ids:
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE id = %s", (delete_id,))
                    results['deleted_count'] += cursor.rowcount
                    logger.info(f"Deleted {table} record {delete_id}")
                except Exception as e:
                    error_msg = f"Error deleting {table} record {delete_id}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
            
            connection.commit()
            cursor.close()
            
            if results['errors']:
                results['success'] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Error during duplicate deletion: {e}", exc_info=True)
            try:
                connection.rollback()
            except:
                pass
            raise


    def apply_pending_migrations(self) -> dict:
        """
        Apply all pending database migrations.
        
        Returns:
            Dictionary with migration results and status messages
        """
        logger.info("Starting migration application")
        
        results = {
            'success': True,
            'messages': [],
            'errors': [],
            'stats': {}
        }
        
        try:
            from db.migration_manager import MigrationManager
            
            # Create migration manager
            migration_manager = MigrationManager(self.db)
            
            # Ensure migrations table exists
            if not migration_manager.ensure_migrations_table():
                results['success'] = False
                results['errors'].append("Αποτυχία δημιουργίας πίνακα migrations")
                return results
            
            # Get pending migrations
            pending = migration_manager.get_pending_migrations()
            
            if not pending:
                results['messages'].append("✓ Δεν υπάρχουν εκκρεμείς migrations")
                results['stats']['pending'] = 0
                results['stats']['applied'] = 0
                return results
            
            results['stats']['pending'] = len(pending)
            results['messages'].append(f"Βρέθηκαν {len(pending)} εκκρεμείς migrations:")
            
            # List pending migrations
            for migration in pending:
                results['messages'].append(f"  • v{migration['version']}: {migration['description']}")
            
            # Apply each migration
            applied_count = 0
            failed_count = 0
            
            for migration in pending:
                try:
                    if migration_manager.apply_migration(migration):
                        applied_count += 1
                        results['messages'].append(f"✓ Migration v{migration['version']} εφαρμόστηκε")
                        logger.info(f"Applied migration v{migration['version']}")
                    else:
                        failed_count += 1
                        error_msg = f"✗ Migration v{migration['version']} απέτυχε"
                        results['errors'].append(error_msg)
                        logger.error(error_msg)
                except Exception as e:
                    failed_count += 1
                    error_msg = f"✗ Migration v{migration['version']}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
            
            results['stats']['applied'] = applied_count
            results['stats']['failed'] = failed_count
            
            if failed_count > 0:
                results['success'] = False
                results['messages'].append(f"\n⚠ {failed_count} migrations απέτυχαν")
            else:
                results['messages'].append(f"\n✓ Όλα τα migrations εφαρμόστηκαν επιτυχώς ({applied_count}/{len(pending)})")
            
            logger.info(f"Migration application completed: {applied_count} applied, {failed_count} failed")
            
            return results
            
        except Exception as e:
            logger.error(f"Critical error during migration application: {e}", exc_info=True)
            results['success'] = False
            results['errors'].append(f"Κρίσιμο σφάλμα: {str(e)}")
            return results
