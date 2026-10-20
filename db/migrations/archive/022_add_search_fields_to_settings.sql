-- Migration 022: Add search field preferences to app_settings
-- Date: 2025-11-24
-- Description: Add columns for storing search field preferences per view

-- Add subscriptions_search_fields column
ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS subscriptions_search_fields TEXT DEFAULT NULL
COMMENT 'JSON array of search fields for subscriptions view';

-- Add reports_search_fields column
ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS reports_search_fields TEXT DEFAULT NULL
COMMENT 'JSON array of search fields for reports view';

-- Note: families_search_fields and payments_search_fields should already exist
-- If they don't exist, add them as well
ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS families_search_fields TEXT DEFAULT NULL
COMMENT 'JSON array of search fields for families view';

ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS payments_search_fields TEXT DEFAULT NULL
COMMENT 'JSON array of search fields for payments view';
