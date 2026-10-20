-- Migration 011: Add subscription codes to existing payments with subscriptions
-- Date: 2025-11-20
-- Description: Updates existing payments that have subscription dates but no subscription_code

-- This migration will:
-- 1. Find all payments with subscription dates but no subscription_code
-- 2. Generate subscription codes for them using the pattern ΣΥΝ-YYYY-NNN

-- Note: This should be run manually if you have existing subscriptions without codes
-- For new installations, this is not needed as codes are generated automatically

-- Step 1: Check how many payments need subscription codes
SELECT 
    COUNT(*) as payments_needing_codes,
    MIN(payment_date) as earliest_payment,
    MAX(payment_date) as latest_payment
FROM payments
WHERE subscription_start_date IS NOT NULL
  AND subscription_end_date IS NOT NULL
  AND (subscription_code IS NULL OR subscription_code = '');

-- Step 2: Generate subscription codes for existing payments
-- This uses a simpler approach that works with MySQL/MariaDB

-- Note: This migration is optional and can be skipped if you don't have existing subscriptions
-- The application will generate codes automatically for new subscriptions

-- Uncomment the following lines if you need to generate codes for existing subscriptions:
/*
-- For each year, generate sequential codes
UPDATE payments p
INNER JOIN (
    SELECT 
        id,
        CONCAT('ΣΥΝ-', YEAR(payment_date), '-', 
               LPAD(ROW_NUMBER() OVER (PARTITION BY YEAR(payment_date) ORDER BY payment_date, id), 3, '0')
        ) as new_code
    FROM payments
    WHERE subscription_start_date IS NOT NULL
      AND subscription_end_date IS NOT NULL
      AND (subscription_code IS NULL OR subscription_code = '')
) AS codes ON p.id = codes.id
SET p.subscription_code = codes.new_code;
*/

-- Step 3: Verify the update
SELECT 
    COUNT(*) as total_subscriptions,
    SUM(CASE WHEN subscription_code IS NOT NULL AND subscription_code != '' THEN 1 ELSE 0 END) as with_codes,
    SUM(CASE WHEN subscription_code IS NULL OR subscription_code = '' THEN 1 ELSE 0 END) as without_codes
FROM payments
WHERE subscription_start_date IS NOT NULL
  AND subscription_end_date IS NOT NULL;

-- Step 4: Show sample of generated codes
SELECT 
    id,
    family_id,
    payment_date,
    subscription_code,
    receipt_no,
    subscription_start_date,
    subscription_end_date
FROM payments
WHERE subscription_start_date IS NOT NULL
  AND subscription_end_date IS NOT NULL
ORDER BY payment_date DESC
LIMIT 10;
