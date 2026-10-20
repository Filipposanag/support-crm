-- Migration 009: Migrate Existing Subscriptions to New Table
-- Transfers subscription data from payments table to subscriptions table
-- Date: 2025-11-19

-- This migration safely migrates existing subscriptions from the payments table
-- to the new subscriptions table without losing any data.

-- Step 1: Insert existing subscriptions into the new subscriptions table
INSERT INTO subscriptions (
    family_id,
    year,
    start_date,
    end_date,
    status,
    payment_id,
    total_amount,
    paid_amount,
    remaining_amount,
    notes,
    created_at,
    updated_at
)
SELECT 
    p.family_id,
    p.year,
    p.subscription_start_date as start_date,
    p.subscription_end_date as end_date,
    -- Determine status based on end date
    CASE 
        WHEN p.subscription_end_date >= CURDATE() THEN 'ACTIVE'
        ELSE 'EXPIRED'
    END as status,
    p.id as payment_id,
    p.total_amount,
    p.paid_amount,
    p.remaining_amount,
    CONCAT('Migrated from payment #', p.id) as notes,
    p.created_at,
    p.updated_at
FROM payments p
WHERE p.subscription_start_date IS NOT NULL
  AND p.subscription_end_date IS NOT NULL
  -- Only migrate if not already in subscriptions table
  AND NOT EXISTS (
      SELECT 1 
      FROM subscriptions s 
      WHERE s.payment_id = p.id
  )
ORDER BY p.id;

-- Step 2: Show migration results
SELECT 
    COUNT(*) as total_migrated,
    SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) as active_count,
    SUM(CASE WHEN status = 'EXPIRED' THEN 1 ELSE 0 END) as expired_count
FROM subscriptions
WHERE notes LIKE 'Migrated from payment%';

-- Step 3: Verify migration - show sample of migrated data
SELECT 
    s.id as subscription_id,
    s.family_id,
    s.year,
    s.start_date,
    s.end_date,
    s.status,
    s.payment_id,
    p.receipt_no,
    f.last_name,
    f.first_name
FROM subscriptions s
JOIN payments p ON s.payment_id = p.id
JOIN families f ON s.family_id = f.id
WHERE s.notes LIKE 'Migrated from payment%'
ORDER BY s.created_at DESC
LIMIT 10;

-- Step 4: Check for any orphaned subscriptions (payments without subscription in new table)
SELECT 
    p.id as payment_id,
    p.family_id,
    p.year,
    p.subscription_start_date,
    p.subscription_end_date,
    p.receipt_no,
    f.last_name
FROM payments p
LEFT JOIN subscriptions s ON s.payment_id = p.id
JOIN families f ON p.family_id = f.id
WHERE p.subscription_start_date IS NOT NULL
  AND p.subscription_end_date IS NOT NULL
  AND s.id IS NULL;

-- Note: The subscription_start_date and subscription_end_date columns in the payments table
-- are NOT removed by this migration. They are kept for backward compatibility and as backup.
-- If you want to remove them later, create a separate migration after thorough testing.

