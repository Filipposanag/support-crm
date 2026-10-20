-- Migration 008: Add subscription_code field to payments table
-- Adds a subscription code field for tracking subscription numbers

-- Add subscription_code field
ALTER TABLE payments
ADD COLUMN IF NOT EXISTS subscription_code VARCHAR(50) COMMENT 'Subscription code (auto-generated)';

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_payments_subscription_code ON payments(subscription_code);
