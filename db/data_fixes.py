"""
Data fixes that run automatically on application startup.
These are one-time fixes for existing data issues.
"""

import logging

logger = logging.getLogger(__name__)


def fix_subscription_amounts(db_connection) -> bool:
    """
    Fix subscription amounts that were incorrectly doubled.
    
    This fix:
    1. Finds subscriptions where amounts don't match their linked payment
    2. Updates subscription amounts to match the payment amounts
    3. Only runs if needed (checks if fix is already applied)
    
    Args:
        db_connection: DatabaseConnection instance
        
    Returns:
        True if fix applied successfully or not needed
    """
    try:
        # Check if fix is needed by counting mismatched subscriptions
        check_query = """
            SELECT COUNT(*) as count
            FROM subscriptions s
            INNER JOIN payments p ON s.payment_id = p.id
            WHERE s.total_amount != p.total_amount 
               OR s.paid_amount != p.paid_amount 
               OR s.remaining_amount != p.remaining_amount
        """
        
        result = db_connection.execute_query(check_query)
        mismatched_count = result[0]['count'] if result else 0
        
        if mismatched_count == 0:
            logger.debug("Subscription amounts are already correct, skipping fix")
            return True
        
        logger.info(f"Found {mismatched_count} subscription(s) with incorrect amounts, applying fix...")
        
        # Apply the fix
        fix_query = """
            UPDATE subscriptions s
            INNER JOIN payments p ON s.payment_id = p.id
            SET 
                s.total_amount = p.total_amount,
                s.paid_amount = p.paid_amount,
                s.remaining_amount = p.remaining_amount,
                s.updated_at = NOW()
            WHERE 
                s.total_amount != p.total_amount 
                OR s.paid_amount != p.paid_amount 
                OR s.remaining_amount != p.remaining_amount
        """
        
        rows_affected = db_connection.execute_update(fix_query)
        
        # Commit the changes
        connection = db_connection.get_connection()
        connection.commit()
        
        logger.info(f"Fixed {rows_affected} subscription amount(s) successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing subscription amounts: {e}", exc_info=True)
        try:
            connection = db_connection.get_connection()
            connection.rollback()
        except:
            pass
        return False


def ensure_org_afm_column(db_connection) -> bool:
    """
    Ensure org_afm column exists in app_settings table.
    Adds the column if it doesn't exist.
    
    Args:
        db_connection: DatabaseConnection instance
        
    Returns:
        True if column exists or was added successfully
    """
    try:
        # Check if column exists
        check_query = """
            SELECT COUNT(*) as count
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'app_settings'
            AND column_name = 'org_afm'
        """
        
        result = db_connection.execute_query(check_query)
        column_exists = result[0]['count'] > 0 if result else False
        
        if column_exists:
            logger.debug("Column org_afm already exists in app_settings")
            return True
        
        logger.info("Adding org_afm column to app_settings table...")
        
        # Add the column
        alter_query = """
            ALTER TABLE app_settings 
            ADD COLUMN org_afm VARCHAR(20) DEFAULT '' 
            COMMENT 'Organization Tax ID (AFM)'
        """
        
        db_connection.execute_update(alter_query)
        
        # Commit the changes
        connection = db_connection.get_connection()
        connection.commit()
        
        logger.info("Column org_afm added successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring org_afm column: {e}", exc_info=True)
        try:
            connection = db_connection.get_connection()
            connection.rollback()
        except:
            pass
        return False


def apply_all_data_fixes(db_connection) -> bool:
    """
    Apply all data fixes.
    Called automatically on application startup.
    
    Args:
        db_connection: DatabaseConnection instance
        
    Returns:
        True if all fixes applied successfully
    """
    try:
        logger.info("Checking for data fixes...")
        
        # List of all data fix functions
        fixes = [
            ("Fix subscription amounts", fix_subscription_amounts),
            ("Ensure org_afm column", ensure_org_afm_column),
        ]
        
        success = True
        for fix_name, fix_func in fixes:
            try:
                logger.debug(f"Applying: {fix_name}")
                if not fix_func(db_connection):
                    logger.warning(f"Fix '{fix_name}' failed, but continuing...")
                    success = False
            except Exception as e:
                logger.error(f"Error applying fix '{fix_name}': {e}")
                success = False
        
        if success:
            logger.info("All data fixes completed successfully")
        else:
            logger.warning("Some data fixes failed, but application will continue")
        
        return success
        
    except Exception as e:
        logger.error(f"Error applying data fixes: {e}")
        return False
