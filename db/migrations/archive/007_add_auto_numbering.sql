-- Migration 007: Add Auto-Numbering Fields
-- Adds counter and prefix fields for automatic numbering of receipts, subscriptions, and families

-- Add auto-numbering fields to app_settings
ALTER TABLE app_settings
ADD COLUMN IF NOT EXISTS receipt_counter INT DEFAULT 1 COMMENT 'Next receipt number',
ADD COLUMN IF NOT EXISTS subscription_counter INT DEFAULT 1 COMMENT 'Next subscription number',
ADD COLUMN IF NOT EXISTS family_counter INT DEFAULT 1 COMMENT 'Next family number',
ADD COLUMN IF NOT EXISTS receipt_prefix VARCHAR(20) DEFAULT 'ΑΠ' COMMENT 'Receipt number prefix',
ADD COLUMN IF NOT EXISTS subscription_prefix VARCHAR(20) DEFAULT 'ΣΥΝ' COMMENT 'Subscription number prefix',
ADD COLUMN IF NOT EXISTS family_prefix VARCHAR(20) DEFAULT 'ΟΙΚ' COMMENT 'Family number prefix';

-- Initialize counters based on existing data (if any)
-- This ensures new numbers start after existing records

-- Update receipt counter based on existing receipt numbers
UPDATE app_settings 
SET receipt_counter = (
    SELECT COALESCE(MAX(CAST(SUBSTRING_INDEX(receipt_no, '-', -1) AS UNSIGNED)), 0) + 1
    FROM payments 
    WHERE receipt_no LIKE 'ΑΠ-%'
)
WHERE id = 1 AND receipt_counter = 1;

-- If no matching receipts found, keep default value of 1
UPDATE app_settings 
SET receipt_counter = 1
WHERE id = 1 AND receipt_counter IS NULL;
