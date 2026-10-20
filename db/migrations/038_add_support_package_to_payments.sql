-- Migration 038: Add support package field to payments
-- Date: 2026-01-24
-- Description: Add support_package field to payments table to track which support package was purchased

-- Add support_package column to payments table
ALTER TABLE payments 
ADD COLUMN IF NOT EXISTS support_package ENUM('hourly', 'monthly', 'yearly', 'custom') DEFAULT NULL 
COMMENT 'Support package type purchased with this payment'
AFTER subscription_code;

-- Add index for support_package queries
ALTER TABLE payments
ADD INDEX IF NOT EXISTS idx_payments_support_package (support_package);
