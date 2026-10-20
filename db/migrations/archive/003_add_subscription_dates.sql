-- Migration: Add subscription date fields to payments table
-- Date: 2025-01-XX
-- Description: Adds subscription_start_date and subscription_end_date fields to support subscription management

-- Add subscription_start_date column
ALTER TABLE payments 
ADD COLUMN subscription_start_date DATE NULL COMMENT 'Subscription start date' 
AFTER year;

-- Add subscription_end_date column
ALTER TABLE payments 
ADD COLUMN subscription_end_date DATE NULL COMMENT 'Subscription end date' 
AFTER subscription_start_date;

-- Add index for subscription date queries
CREATE INDEX idx_payments_subscription_dates 
ON payments(subscription_start_date, subscription_end_date);

-- Update existing records to set subscription dates based on year
-- For existing payments, set subscription period to full calendar year
UPDATE payments 
SET 
    subscription_start_date = CONCAT(year, '-01-01'),
    subscription_end_date = CONCAT(year, '-12-31')
WHERE year IS NOT NULL 
  AND subscription_start_date IS NULL 
  AND subscription_end_date IS NULL;
