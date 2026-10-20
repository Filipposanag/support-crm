-- Migration: Make legacy_pcode nullable
-- Date: 2025-11-17
-- Reason: legacy_pcode is only needed for imported data from report.csv
--         New payments created through the UI don't have a legacy_pcode

-- Make legacy_pcode nullable
ALTER TABLE payments 
MODIFY COLUMN legacy_pcode INT NULL COMMENT 'Legacy PCODE from report.csv (nullable for new payments)';

-- Verify the change
DESCRIBE payments;
