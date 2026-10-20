-- Migration 014: Add subscription_code column to subscriptions table
-- Description: Add subscription_code to subscriptions for easier search and display
-- Date: November 20, 2025

-- ============================================================================
-- Add subscription_code column to subscriptions table
-- ============================================================================

ALTER TABLE subscriptions 
ADD COLUMN IF NOT EXISTS subscription_code VARCHAR(50) COMMENT 'Subscription code (copied from payment)' 
AFTER payment_id;

-- Add index for fast search (only if it doesn't exist)
CREATE INDEX IF NOT EXISTS idx_subscriptions_code ON subscriptions(subscription_code);

-- ============================================================================
-- Migrate existing data: Copy subscription_code from payments to subscriptions
-- ============================================================================

UPDATE subscriptions s
INNER JOIN payments p ON s.payment_id = p.id
SET s.subscription_code = p.subscription_code
WHERE p.subscription_code IS NOT NULL;

-- ============================================================================
-- Mark migration as applied
-- ============================================================================
INSERT INTO schema_migrations (version, description)
VALUES (14, 'Add subscription_code column to subscriptions table')
ON DUPLICATE KEY UPDATE description=description;
