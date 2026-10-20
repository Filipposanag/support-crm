#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migration Script: Add subscription codes to existing payments
Date: 2025-11-20

This script updates existing payments that have subscription dates but no subscription_code.
It generates codes in the format: ΣΥΝ-YYYY-NNN
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.connection import DatabaseConnection
from configurator.config_service import ConfigService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def update_subscription_codes():
    """Update subscription codes for existing payments."""
    try:
        # Get database configuration
        config_service = ConfigService()
        db_config = config_service.load_config()
        
        # Create database connection
        db = DatabaseConnection(db_config)
        
        logger.info("Connected to database")
        
        # Step 1: Find payments that need subscription codes
        query_check = """
            SELECT 
                id,
                family_id,
                payment_date,
                subscription_start_date,
                subscription_end_date,
                subscription_code
            FROM payments
            WHERE subscription_start_date IS NOT NULL
              AND subscription_end_date IS NOT NULL
              AND (subscription_code IS NULL OR subscription_code = '')
            ORDER BY payment_date, id
        """
        
        payments_needing_codes = db.execute_query(query_check)
        
        if not payments_needing_codes:
            logger.info("No payments need subscription codes. All done!")
            return
        
        logger.info(f"Found {len(payments_needing_codes)} payments that need subscription codes")
        
        # Step 2: Generate subscription codes grouped by year
        year_counters = {}
        updates = []
        
        for payment in payments_needing_codes:
            payment_id = payment['id']
            payment_date = payment['payment_date']
            
            # Get year from payment_date
            if isinstance(payment_date, str):
                year = int(payment_date[:4])
            else:
                year = payment_date.year
            
            # Initialize counter for this year if not exists
            if year not in year_counters:
                year_counters[year] = 0
            
            # Increment counter
            year_counters[year] += 1
            counter = year_counters[year]
            
            # Generate subscription code
            subscription_code = f"ΣΥΝ-{year}-{counter:03d}"
            
            updates.append((subscription_code, payment_id))
            
            logger.debug(f"Payment ID {payment_id}: {subscription_code}")
        
        # Step 3: Update database
        logger.info(f"Updating {len(updates)} payments with subscription codes...")
        
        update_query = """
            UPDATE payments
            SET subscription_code = %s
            WHERE id = %s
        """
        
        connection = db.get_connection()
        cursor = connection.cursor()
        
        for subscription_code, payment_id in updates:
            cursor.execute(update_query, (subscription_code, payment_id))
        
        connection.commit()
        cursor.close()
        
        logger.info(f"Successfully updated {len(updates)} payments")
        
        # Step 4: Verify
        verify_query = """
            SELECT 
                COUNT(*) as total_subscriptions,
                SUM(CASE WHEN subscription_code IS NOT NULL AND subscription_code != '' THEN 1 ELSE 0 END) as with_codes,
                SUM(CASE WHEN subscription_code IS NULL OR subscription_code = '' THEN 1 ELSE 0 END) as without_codes
            FROM payments
            WHERE subscription_start_date IS NOT NULL
              AND subscription_end_date IS NOT NULL
        """
        
        result = db.execute_query(verify_query)
        if result:
            stats = result[0]
            logger.info(f"Verification:")
            logger.info(f"  Total subscriptions: {stats['total_subscriptions']}")
            logger.info(f"  With codes: {stats['with_codes']}")
            logger.info(f"  Without codes: {stats['without_codes']}")
        
        # Step 5: Show sample
        sample_query = """
            SELECT 
                id,
                payment_date,
                subscription_code,
                receipt_no
            FROM payments
            WHERE subscription_start_date IS NOT NULL
              AND subscription_end_date IS NOT NULL
            ORDER BY payment_date DESC
            LIMIT 5
        """
        
        samples = db.execute_query(sample_query)
        logger.info("Sample of updated payments:")
        for sample in samples:
            logger.info(f"  ID {sample['id']}: {sample['subscription_code']} (Receipt: {sample['receipt_no']})")
        
        # Close connection
        db.close()
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    logger.info("Starting subscription codes migration...")
    update_subscription_codes()
